import os
import uuid
import telebot
import yt_dlp
import ffmpeg
import json
import sqlite3
import threading
import time
from flask import Flask, request
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

# --- LOGGING AYARLARI ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- AYARLAR ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY')  # Environment variable'dan al
bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("ZB_MUSIC")
TEMP_DIR.mkdir(exist_ok=True)

# --- VERİTABANI AYARLARI ---
DB_PATH = Path("bot_data.db")

# --- KURUCU VE ADMIN SİSTEMİ ---
OWNER_ID = int(os.environ.get('OWNER_ID', '1275184751'))  # Environment variable'dan al
ADMIN_USERS = {OWNER_ID}

# --- ÖNBELLEK VE SINIRLAMALAR ---
search_cache: Dict[str, tuple] = {}
CACHE_TIME = 300  # 5 dakika
MAX_CONCURRENT_DOWNLOADS = 3  # Maksimum eşzamanlı indirme
active_downloads = 0
download_lock = threading.Lock()

# --- VERİTABANI FONKSİYONLARI ---
def init_database():
    """Veritabanını başlat"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Kullanıcı verileri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER PRIMARY KEY,
            bitrate TEXT DEFAULT '320k',
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            download_count INTEGER DEFAULT 0
        )
    ''')

    # Arama sonuçları tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_results (
            user_id INTEGER,
            query TEXT,
            results TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, query)
        )
    ''')

    # Admin listesi tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def load_user_data(user_id: int) -> Dict:
    """Kullanıcı verilerini veritabanından yükle"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('SELECT bitrate, download_count FROM user_data WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {'bitrate': row[0], 'download_count': row[1]}
    return {'bitrate': '320k', 'download_count': 0}

def save_user_data(user_id: int, data: Dict):
    """Kullanıcı verilerini veritabanına kaydet"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_data (user_id, bitrate, last_activity, download_count)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?)
    ''', (user_id, data.get('bitrate', '320k'), data.get('download_count', 0)))
    conn.commit()
    conn.close()

def load_admins():
    """Admin listesini veritabanından yükle"""
    global ADMIN_USERS
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM admins')
    admins = cursor.fetchall()
    conn.close()

    ADMIN_USERS = {OWNER_ID}
    for admin in admins:
        ADMIN_USERS.add(admin[0])

def save_admin(user_id: int, added_by: int):
    """Admin ekle"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)', (user_id, added_by))
    conn.commit()
    conn.close()
    ADMIN_USERS.add(user_id)

def remove_admin_from_db(user_id: int):
    """Admin kaldır"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    ADMIN_USERS.discard(user_id)

def cleanup_old_data():
    """Eski verileri temizle"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 30 günden eski arama sonuçlarını sil
    cursor.execute('DELETE FROM search_results WHERE timestamp < datetime("now", "-30 days")')

    # 7 günden eski kullanıcı verilerini sil (aktif olmayan)
    cursor.execute('DELETE FROM user_data WHERE last_activity < datetime("now", "-7 days")')

    conn.commit()
    conn.close()

    # Geçici dosyaları temizle (1 saatten eski)
    current_time = time.time()
    for file_path in TEMP_DIR.glob('*'):
        if file_path.is_file() and current_time - file_path.stat().st_mtime > 3600:  # 1 saat
            try:
                file_path.unlink()
                logger.info(f"Eski dosya temizlendi: {file_path}")
            except Exception as e:
                logger.error(f"Dosya silinirken hata: {e}")

# --- FLASK SUNUCUSU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🎵 ZB MUSIC Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
        return "OK", 200

# --- MÜZİK İNDİRME VE DÖNÜŞTÜRME ---
def arama_yap(query: str, limit: int = 5) -> List[Dict]:
    """YouTube'da arama yap ve sonuçları döndür (önbellek ile hızlandırılmış)"""
    import time

    # Önbellek kontrolü
    cache_key = query.lower().strip()
    if cache_key in search_cache:
        results, timestamp = search_cache[cache_key]
        if time.time() - timestamp < CACHE_TIME:
            logger.info(f"⚡ Önbellekten arama sonucu getirildi: {query}")
            return results

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_json': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            results = info['entries'] if info and 'entries' in info else []

            # Önbelleğe kaydet
            search_cache[cache_key] = (results, time.time())

            # Eski önbellek girişlerini temizle
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in search_cache.items() if current_time - ts > CACHE_TIME]
            for k in expired_keys:
                del search_cache[k]

            return results
    except Exception as e:
        logger.error(f"Arama hatası: {e}")
        return []

def indir_ve_donustur(video_id: str, bitrate: str = '320k', format_type: str = 'audio') -> Path:
    """Belirli bir video ID'sini indir ve MP3'e dönüştür veya video olarak indir (gelişmiş versiyon)"""
    global active_downloads

    with download_lock:
        if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
            raise Exception("Maksimum eşzamanlı indirme sınırına ulaşıldı. Lütfen bekleyin.")

        active_downloads += 1

    try:
        unique_id = str(uuid.uuid4())
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        if format_type == 'audio':
            mp3_path = TEMP_DIR / f"{unique_id}.mp3"
            temp_path = TEMP_DIR / f"{unique_id}"
            output_format = 'bestaudio/best'
        else:
            video_path = TEMP_DIR / f"{unique_id}.mp4"
            temp_path = TEMP_DIR / f"{unique_id}"
            output_format = 'best[height<=720]/best'

        # Çerezleri environment variable'dan al
        yt_cookies = os.environ.get('YT_COOKIES', '')

        # İndirme seçenekleri - daha az kaynak kullanımı için optimize edilmiş
        ydl_opts = {
            'format': output_format,
            'outtmpl': str(temp_path.with_suffix('.%(ext)s')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'referer': 'https://www.youtube.com/',
        }

        # Eğer YT_COOKIES varsa ekle
        if yt_cookies:
            ydl_opts['cookiefile'] = 'cookies.txt'
            with open('cookies.txt', 'w', encoding='utf-8') as f:
                f.write(yt_cookies)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            downloaded_file = next(TEMP_DIR.glob(f"{unique_id}.*"))

            if format_type == 'audio':
                ffmpeg.input(str(downloaded_file)).output(str(mp3_path), audio_bitrate=bitrate).run(overwrite_output=True)
                downloaded_file.unlink()
                result_path = mp3_path
            else:
                ffmpeg.input(str(downloaded_file)).output(str(video_path), vcodec='libx264', acodec='aac').run(overwrite_output=True)
                downloaded_file.unlink()
                result_path = video_path

            # Temizlik
            if yt_cookies and os.path.exists('cookies.txt'):
                os.remove('cookies.txt')

            return result_path

        except Exception as e:
            # Temizlik
            if yt_cookies and os.path.exists('cookies.txt'):
                os.remove('cookies.txt')

            # Geçici dosyaları temizle
            for temp_file in TEMP_DIR.glob(f"{unique_id}.*"):
                try:
                    temp_file.unlink()
                except:
                    pass
            raise e

    finally:
        with download_lock:
            active_downloads -= 1

def format_sure(saniye) -> str:
    """Saniyeyi dakika:saniye formatına dönüştür"""
    try:
        saniye_int = int(float(saniye))
        dakika = saniye_int // 60
        saniye_kalan = saniye_int % 60
        return f"{dakika}:{saniye_kalan:02d}"
    except (ValueError, TypeError):
        return "Bilinmiyor"

# --- BOT KOMUTLARI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_data = load_user_data(user_id)

    welcome_text = """🎶 *ZB MUSIC Bot'a Hoş Geldiniz!*

🤖 *Kullanılabilir Komutlar:*
/start - Botu başlat
/getid - Chat ID'nizi göster
/help - Yardım menüsü
/ayarlar - Ses kalitesi ayarları

🎵 *Nasıl Kullanılır:*
1. Şarkı adı veya sanatçı ismi yazın
2. Arama sonuçlarından birini seçin
3. MP3 olarak indirin!

⚡ *Özellikler:*
• 128kbps, 192kbps, 320kbps ses kaliteleri
• 5 farklı arama sonucu
• Şarkı bilgileri (süre, sanatçı)
• Hızlı indirme

_Her türlü sorunuz için /help yazabilirsiniz._"""

    try:
        bot.reply_to(message, welcome_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Welcome mesajı gönderilirken hata: {e}")

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    try:
        bot.reply_to(message, f"🆔 Chat ID'niz: `{message.chat.id}`", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Chat ID gönderilirken hata: {e}")

@bot.message_handler(commands=['help'])
def send_help(message):
    user_id = message.chat.id
    is_admin = user_id in ADMIN_USERS

    help_text = """❓ *Yardım Menüsü*

🔍 *Arama Yapma:*
Sadece şarkı adı veya sanatçı ismi yazın. Örnek:
• `tarkan kiss kiss`
• `müslüm gürses affet`
• `sezen aksu şarkıları`

⚙️ *Ses Kalitesi:*
/ayarlar komutu ile ses kalitesini değiştirebilirsiniz.

🎮 *Premium Özellikler:*
• Müzik oynatma kontrolü
• Video indirme
• Oyunlar (/oyunlar)
• Özel komutlar

📊 *Limitler:*
• Maximum 10 dakika şarkı süresi

🚨 *Sorun Giderme:*
Eğer şarkı indirilemezse, farklı bir arama terimi deneyin."""

    if is_admin:
        help_text += """

👑 *Admin Komutları:*
• /admin - Admin paneli
• /addadmin [ID] - Admin ekle
• /removeadmin [ID] - Admin kaldır
• /stats - Bot istatistikleri
• /broadcast [mesaj] - Tüm kullanıcılara mesaj gönder"""

    help_text += """

📞 *Destek:*
Sorunlarınız için @btelegram286"""

    try:
        bot.reply_to(message, help_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Help mesajı gönderilirken hata: {e}")

@bot.message_handler(commands=['ayarlar'])
def show_settings(message):
    user_id = message.chat.id
    user_data = load_user_data(user_id)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("128kbps", callback_data="bitrate_128"),
        telebot.types.InlineKeyboardButton("192kbps", callback_data="bitrate_192"),
        telebot.types.InlineKeyboardButton("320kbps", callback_data="bitrate_320")
    )

    try:
        bot.send_message(user_id, f"🎚️ *Mevcut Ses Kalitesi: {user_data['bitrate']}*\n\nYeni kalite seçin:",
                        reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ayarlar mesajı gönderilirken hata: {e}")

# --- ADMIN KOMUTLARI ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.chat.id
    if user_id not in ADMIN_USERS:
        try:
            bot.reply_to(message, "❌ Bu komut sadece adminler için geçerlidir.")
        except Exception as e:
            logger.error(f"Admin yetki hatası mesajı gönderilirken hata: {e}")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("👥 Admin Listesi", callback_data="admin_list"),
        telebot.types.InlineKeyboardButton("📊 İstatistikler", callback_data="admin_stats")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        telebot.types.InlineKeyboardButton("🗑️ Önbelleği Temizle", callback_data="admin_clear_cache")
    )

    try:
        bot.send_message(user_id, "👑 *Admin Paneli*\n\nNe yapmak istiyorsunuz?", reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Admin paneli mesajı gönderilirken hata: {e}")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        try:
            bot.reply_to(message, "❌ Bu komut sadece kurucu için geçerlidir.")
        except Exception as e:
            logger.error(f"Add admin yetki hatası mesajı gönderilirken hata: {e}")
        return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Kullanım: /addadmin [kullanıcı_id]\n\nÖrnek: /addadmin 123456789")
            return

        new_admin_id = int(parts[1])

        if new_admin_id <= 0:
            bot.reply_to(message, "❌ Geçersiz kullanıcı ID. ID pozitif bir sayı olmalıdır.")
            return

        if new_admin_id == OWNER_ID:
            bot.reply_to(message, "❌ Kurucu zaten admin.")
            return

        if new_admin_id in ADMIN_USERS:
            bot.reply_to(message, "❌ Bu kullanıcı zaten admin.")
            return

        save_admin(new_admin_id, user_id)
        bot.reply_to(message, f"✅ Kullanıcı {new_admin_id} admin olarak eklendi.")
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz kullanıcı ID. Lütfen sayısal bir değer girin.")
    except Exception as e:
        logger.error(f"Admin eklenirken hata: {e}")
        bot.reply_to(message, f"❌ Bir hata oluştu: {str(e)}")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        try:
            bot.reply_to(message, "❌ Bu komut sadece kurucu için geçerlidir.")
        except Exception as e:
            logger.error(f"Remove admin yetki hatası mesajı gönderilirken hata: {e}")
        return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Kullanım: /removeadmin [kullanıcı_id]\n\nÖrnek: /removeadmin 123456789")
            return

        remove_admin_id = int(parts[1])

        if remove_admin_id == OWNER_ID:
            bot.reply_to(message, "❌ Kurucuyu admin listesinden çıkaramazsınız.")
            return

        if remove_admin_id not in ADMIN_USERS:
            bot.reply_to(message, "❌ Bu kullanıcı admin değil.")
            return

        remove_admin_from_db(remove_admin_id)
        bot.reply_to(message, f"✅ Kullanıcı {remove_admin_id} admin listesinden çıkarıldı.")
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz kullanıcı ID. Lütfen sayısal bir değer girin.")
    except Exception as e:
        logger.error(f"Admin çıkarılırken hata: {e}")
        bot.reply_to(message, f"❌ Bir hata oluştu: {str(e)}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.chat.id
    if user_id not in ADMIN_USERS:
        try:
            bot.reply_to(message, "❌ Bu komut sadece adminler için geçerlidir.")
        except Exception as e:
            logger.error(f"Stats yetki hatası mesajı gönderilirken hata: {e}")
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM user_data')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM search_results')
        total_searches = cursor.fetchone()[0]

        admin_count = len(ADMIN_USERS)
        cache_size = len(search_cache)

        conn.close()

        stats_text = f"""📊 *Bot İstatistikleri*

👥 Toplam Kullanıcı: {total_users}
🔍 Aktif Aramalar: {total_searches}
⚡ Önbellek Boyutu: {cache_size}
👑 Admin Sayısı: {admin_count}

💾 Geçici Dosyalar: {len(list(TEMP_DIR.glob('*')))}"""

        bot.reply_to(message, stats_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"İstatistikler alınırken hata: {e}")
        bot.reply_to(message, "❌ İstatistikler alınırken bir hata oluştu.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data

    try:
        if data.startswith('bitrate_'):
            bitrate = data.split('_')[1] + 'k'
            user_data = load_user_data(user_id)
            user_data['bitrate'] = bitrate
            save_user_data(user_id, user_data)

            bot.answer_callback_query(call.id, f"Ses kalitesi {bitrate} olarak ayarlandı!")
            bot.edit_message_text(f"✅ Ses kalitesi *{bitrate}* olarak güncellendi!",
                                 user_id, call.message.message_id, parse_mode='Markdown')

        elif data.startswith('download_'):
            video_id = data.split('_')[1]
            user_data = load_user_data(user_id)
            bitrate = user_data.get('bitrate', '320k')

            bot.answer_callback_query(call.id, "⏳ Şarkı indiriliyor...")

            try:
                mp3_file = indir_ve_donustur(video_id, bitrate)

                # İndirme sayısını güncelle
                user_data['download_count'] = user_data.get('download_count', 0) + 1
                save_user_data(user_id, user_data)

                # Şarkı bilgilerini al (önbellekten)
                results = search_cache.get(f"download_{video_id}", ([], 0))[0]
                if not results:
                    # Basit şarkı bilgisi
                    song_info = {'title': 'İndirilen Şarkı', 'duration': 0}
                else:
                    song_info = results[0] if results else {'title': 'İndirilen Şarkı', 'duration': 0}

                caption = f"🎵 {song_info['title']}"
                if 'duration' in song_info and song_info['duration']:
                    caption += f"\n⏱️ {format_sure(song_info['duration'])}"

                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(
                    telebot.types.InlineKeyboardButton("✅ Listeye Ekle", callback_data=f"addlist_{video_id}"),
                    telebot.types.InlineKeyboardButton("🔮 Kontrol Paneli", callback_data=f"controlpanel_{video_id}")
                )

                with open(mp3_file, 'rb') as audio:
                    bot.send_audio(user_id, audio, caption=caption, reply_markup=markup, parse_mode='Markdown')

                # Dosyayı temizle
                mp3_file.unlink()

            except Exception as e:
                logger.error(f"İndirme hatası: {e}")
                bot.send_message(user_id, f"❌ İndirme hatası: {str(e)}")

        elif data == 'admin_list':
            if user_id not in ADMIN_USERS:
                bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
                return

            admin_list = "\n".join([f"• {admin_id}" for admin_id in ADMIN_USERS])
            bot.send_message(user_id, f"👑 *Admin Listesi:*\n\n{admin_list}", parse_mode='Markdown')

        elif data == 'admin_stats':
            if user_id not in ADMIN_USERS:
                bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
                return

            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM user_data')
            total_users = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM search_results')
            total_searches = cursor.fetchone()[0]

            admin_count = len(ADMIN_USERS)
            cache_size = len(search_cache)

            conn.close()

            stats_text = f"""📊 *Bot İstatistikleri*

👥 Toplam Kullanıcı: {total_users}
🔍 Aktif Aramalar: {total_searches}
⚡ Önbellek Boyutu: {cache_size}
👑 Admin Sayısı: {admin_count}

💾 Geçici Dosyalar: {len(list(TEMP_DIR.glob('*')))}"""

            bot.send_message(user_id, stats_text, parse_mode='Markdown')

        elif data == 'admin_clear_cache':
            if user_id not in ADMIN_USERS:
                bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
                return

            cache_count = len(search_cache)
            search_cache.clear()
            bot.send_message(user_id, f"✅ Önbellek temizlendi!\n🗑️ Temizlenen giriş sayısı: {cache_count}")

    except Exception as e:
        logger.error(f"Callback işlenirken hata: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Bir hata oluştu!")
        except:
            pass

@bot.message_handler(func=lambda m: True)
def handle_query(message):
    user_id = message.chat.id
    query = message.text.strip()

    if not query:
        try:
            bot.reply_to(message, "❌ Lütfen bir şarkı adı veya sanatçı ismi yazın.")
        except Exception as e:
            logger.error(f"Boş query hatası mesajı gönderilirken hata: {e}")
        return

    try:
        bot.reply_to(message, "🔍 YouTube'da aranıyor...")

        # Arama yap
        results = arama_yap(query, 5)

        if not results:
            bot.reply_to(message, "❌ Arama sonucu bulunamadı. Farklı bir terim deneyin.")
            return

        # Sonuçları önbelleğe kaydet
        search_cache[f"query_{user_id}"] = (results, time.time())

        # Inline keyboard oluştur
        markup = telebot.types.InlineKeyboardMarkup()
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', 'Bilinmeyen')
            duration = format_sure(result.get('duration', 0)) if result.get('duration') else 'Bilinmiyor'
            markup.row(telebot.types.InlineKeyboardButton(
                f"{i}. {title[:30]}... ({duration})",
                callback_data=f"download_{result['id']}"
            ))

        bot.send_message(user_id, f"🎵 *Arama Sonuçları:*\n\nAramak için: `{query}`\n\nİndirmek istediğiniz şarkıyı seçin:",
                        reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Query işlenirken hata: {e}")
        try:
            bot.reply_to(message, f"❌ Bir hata oluştu:\n{str(e)}")
        except Exception as reply_error:
            logger.error(f"Hata mesajı gönderilirken hata: {reply_error}")

# --- TEMİZLİK THREAD'İ ---
def cleanup_thread():
    """Düzenli temizlik işlemleri"""
    while True:
        try:
            cleanup_old_data()
            time.sleep(3600)  # Her saat başı temizle
        except Exception as e:
            logger.error(f"Temizlik işlemi hatası: {e}")
            time.sleep(300)  # Hata durumunda 5 dakika bekle

# --- SUNUCUYU BAŞLAT ---
if __name__ == "__main__":
    print("🚀 ZB MUSIC Bot başlatılıyor...")

    # Veritabanını başlat
    init_database()
    load_admins()

    # Temizlik thread'ini başlat
    cleanup_thread_instance = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_thread_instance.start()

    try:
        # Webhook URL'sini ayarla (Render için)
        WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
        if WEBHOOK_URL:
            bot.remove_webhook()
            bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
            print("📡 Bot webhook modunda çalışıyor...")
            app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
        else:
            # Local development için polling
            print("📡 Bot polling modunda çalışıyor...")
            bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"❌ Bot başlatılırken hata oluştu: {e}")
