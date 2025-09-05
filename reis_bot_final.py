import os
import uuid
import telebot
import yt_dlp
import ffmpeg
import json
from flask import Flask, request
from pathlib import Path
from typing import Dict, List, Optional

# --- AYARLAR ---
BOT_TOKEN = "8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY"  # Gerçek token
bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("ZB_MUSIC")
TEMP_DIR.mkdir(exist_ok=True)

# --- KURUCU VE ADMIN SİSTEMİ ---
OWNER_ID = 1275184751  # Kurucu ID'si (kullanıcının kendi ID'si)
ADMIN_USERS = {OWNER_ID}  # Admin kullanıcıları
ADMIN_FILE = Path("admin_users.json")  # Admin listesini kaydetmek için

# Kullanıcı verileri ve arama sonuçları için geçici depolama
user_data: Dict[int, Dict] = {}
search_results: Dict[str, List[Dict]] = {}

# --- ÖNBELLEK SİSTEMİ (HIZ İÇİN) ---
search_cache: Dict[str, tuple] = {}  # query -> (results, timestamp)
CACHE_TIME = 300  # 5 dakika önbellek

# --- ADMIN YÖNETİM FONKSİYONLARI ---
def load_admin_users():
    """Admin listesini dosyadan yükle"""
    global ADMIN_USERS
    try:
        if ADMIN_FILE.exists():
            with open(ADMIN_FILE, 'r', encoding='utf-8') as f:
                admin_list = json.load(f)
                ADMIN_USERS = set(admin_list)
                ADMIN_USERS.add(OWNER_ID)  # Kurucuyu her zaman ekle
    except Exception as e:
        print(f"Admin listesi yüklenirken hata: {e}")
        ADMIN_USERS = {OWNER_ID}

def save_admin_users():
    """Admin listesini dosyaya kaydet"""
    try:
        with open(ADMIN_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(ADMIN_USERS), f, indent=2)
    except Exception as e:
        print(f"Admin listesi kaydedilirken hata: {e}")

# Başlangıçta admin listesini yükle
load_admin_users()

# --- FLASK SUNUCUSU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🎵 ZB MUSIC Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
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
            print(f"⚡ Önbellekten arama sonucu getirildi: {query}")
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
    except Exception:
        return []

def indir_ve_donustur(video_id: str, bitrate: str = '320k', format_type: str = 'audio') -> Path:
    """Belirli bir video ID'sini indir ve MP3'e dönüştür veya video olarak indir (gelişmiş versiyon)"""
    unique_id = str(uuid.uuid4())
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    if format_type == 'audio':
        mp3_path = TEMP_DIR / f"{unique_id}.mp3"
        temp_path = TEMP_DIR / f"{unique_id}"
        output_format = 'bestaudio/best'
    else:  # video
        video_path = TEMP_DIR / f"{unique_id}.mp4"
        temp_path = TEMP_DIR / f"{unique_id}"
        output_format = 'best[height<=720]/best'

    # Çerezleri environment variable'dan al
    yt_cookies = os.environ.get('YT_COOKIES', '')

    # İndirme seçenekleri - önce normal, sonra Android client ile dene
    ydl_opts_list = [
        # 1. Deneme: Normal web client + çerezler
        {
            'format': output_format,
            'outtmpl': str(temp_path.with_suffix('.%(ext)s')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['web']
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 3,
        },
        # 2. Deneme: Android client + çerezler
        {
            'format': output_format,
            'outtmpl': str(temp_path.with_suffix('.%(ext)s')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android']
                }
            },
            'user_agent': 'com.google.android.youtube/18.31.40 (Linux; Android 12)',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 3,
        },
        # 3. Deneme: Mobil user-agent ile
        {
            'format': output_format,
            'outtmpl': str(temp_path.with_suffix('.%(ext)s')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'user_agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 3,
        }
    ]

    # Eğer YT_COOKIES environment variable varsa, geçici cookies.txt oluştur
    if yt_cookies:
        with open('cookies.txt', 'w', encoding='utf-8') as f:
            f.write(yt_cookies)
        # Çerez dosyası kullanılacak şekilde tüm seçenekleri güncelle
        for opts in ydl_opts_list:
            opts['cookiefile'] = 'cookies.txt'

    last_error = None
    for i, ydl_opts in enumerate(ydl_opts_list, 1):
        try:
            print(f"⏳ İndirme denemesi {i}/3: {ydl_opts.get('user_agent', 'default')}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            downloaded_file = next(TEMP_DIR.glob(f"{unique_id}.*"))

            if format_type == 'audio':
                ffmpeg.input(str(downloaded_file)).output(str(mp3_path), audio_bitrate=bitrate).run(overwrite_output=True)
                downloaded_file.unlink()
                result_path = mp3_path
            else:
                # Video için sadece yeniden kodlama yap
                ffmpeg.input(str(downloaded_file)).output(str(video_path), vcodec='libx264', acodec='aac').run(overwrite_output=True)
                downloaded_file.unlink()
                result_path = video_path

            # Temizlik: Geçici cookies.txt dosyasını sil
            if yt_cookies and os.path.exists('cookies.txt'):
                os.remove('cookies.txt')

            return result_path

        except Exception as e:
            last_error = e
            print(f"❌ Deneme {i} başarısız: {str(e)}")
            # Önceki denemede oluşan geçici dosyaları temizle
            for temp_file in TEMP_DIR.glob(f"{unique_id}.*"):
                try:
                    temp_file.unlink()
                except:
                    pass
            continue

    # Temizlik: Geçici cookies.txt dosyasını sil
    if yt_cookies and os.path.exists('cookies.txt'):
        os.remove('cookies.txt')

    raise Exception(f"Tüm indirme denemeleri başarısız: {last_error}")

def format_sure(saniye) -> str:
    """Saniyeyi dakika:saniye formatına dönüştür"""
    try:
        # Float veya int değeri integer'a dönüştür
        saniye_int = int(float(saniye))
        dakika = saniye_int // 60
        saniye_kalan = saniye_int % 60
        return f"{dakika}:{saniye_kalan:02d}"
    except (ValueError, TypeError):
        return "Bilinmiyor"

# --- BOT KOMUTLARI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
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
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    bot.reply_to(message, f"🆔 Chat ID'niz: `{message.chat.id}`", parse_mode='Markdown')

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

    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['oyunlar'])
def show_games(message):
    user_id = message.chat.id
    premium_users = {123456789}  # Buraya premium kullanıcı ID'leri eklenecek

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎲 Sayı Tahmin Oyunu", callback_data="game_number_guess"),
        telebot.types.InlineKeyboardButton("🪨 Taş Kağıt Makas", callback_data="game_rock_paper_scissors")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎯 Hedef Atışı", callback_data="game_target_shoot"),
        telebot.types.InlineKeyboardButton("🧠 Hafıza Oyunu", callback_data="game_memory")
    )

    bot.send_message(user_id, "🎮 *Premium Oyunlar*\n\nHangi oyunu oynamak istiyorsunuz?", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['video'])
def handle_video_command(message):
    user_id = message.chat.id
    premium_users = {123456789}  # Buraya premium kullanıcı ID'leri eklenecek

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Video indirme özelliği premium kullanıcılar için geçerlidir.")
        return

    query = message.text.replace('/video', '').strip()
    if not query:
        bot.reply_to(message, "❌ Lütfen video arama terimi girin. Örnek: `/video türkçe şarkı`")
        return

    try:
        bot.reply_to(message, "🔍 YouTube'da video aranıyor...")

        # Arama yap
        results = arama_yap(query, 5)

        if not results:
            bot.reply_to(message, "❌ Arama sonucu bulunamadı. Farklı bir terim deneyin.")
            return

        # Sonuçları sakla
        search_results[str(user_id)] = results

        # Inline keyboard oluştur
        markup = telebot.types.InlineKeyboardMarkup()
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', 'Bilinmeyen')
            duration = format_sure(result.get('duration', 0)) if result.get('duration') else 'Bilinmiyor'
            markup.row(telebot.types.InlineKeyboardButton(
                f"{i}. {title[:30]}... ({duration})",
                callback_data=f"download_video_{result['id']}"
            ))

        bot.send_message(user_id, f"🎥 *Video Arama Sonuçları:*\n\nAramak için: `{query}`\n\nİndirmek istediğiniz videoyu seçin:",
                        reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Bir hata oluştu:\n{str(e)}")

@bot.message_handler(commands=['ayarlar'])
def show_settings(message):
    user_id = message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {'bitrate': '320k'}

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("128kbps", callback_data="bitrate_128"),
        telebot.types.InlineKeyboardButton("192kbps", callback_data="bitrate_192"),
        telebot.types.InlineKeyboardButton("320kbps", callback_data="bitrate_320")
    )

    bot.send_message(user_id, f"🎚️ *Mevcut Ses Kalitesi: {user_data[user_id]['bitrate']}*\n\nYeni kalite seçin:",
                    reply_markup=markup, parse_mode='Markdown')

# --- ADMIN KOMUTLARI ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.chat.id
    if user_id not in ADMIN_USERS:
        bot.reply_to(message, "❌ Bu komut sadece adminler için geçerlidir.")
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

    bot.send_message(user_id, "👑 *Admin Paneli*\n\nNe yapmak istiyorsunuz?", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Bu komut sadece kurucu için geçerlidir.")
        return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Kullanım: /addadmin [kullanıcı_id]\n\nÖrnek: /addadmin 123456789")
            return

        new_admin_id = int(parts[1])

        # Geçerli ID kontrolü
        if new_admin_id <= 0:
            bot.reply_to(message, "❌ Geçersiz kullanıcı ID. ID pozitif bir sayı olmalıdır.")
            return

        if new_admin_id == OWNER_ID:
            bot.reply_to(message, "❌ Kurucu zaten admin.")
            return

        if new_admin_id in ADMIN_USERS:
            bot.reply_to(message, "❌ Bu kullanıcı zaten admin.")
            return

        ADMIN_USERS.add(new_admin_id)
        save_admin_users()  # Admin listesini kaydet
        bot.reply_to(message, f"✅ Kullanıcı {new_admin_id} admin olarak eklendi.\n\n📝 Admin listesi kaydedildi.")
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz kullanıcı ID. Lütfen sayısal bir değer girin.")
    except Exception as e:
        bot.reply_to(message, f"❌ Bir hata oluştu: {str(e)}")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Bu komut sadece kurucu için geçerlidir.")
        return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Kullanım: /removeadmin [kullanıcı_id]\n\nÖrnek: /removeadmin 123456789")
            return

        remove_admin_id = int(parts[1])

        # Geçerli ID kontrolü
        if remove_admin_id <= 0:
            bot.reply_to(message, "❌ Geçersiz kullanıcı ID. ID pozitif bir sayı olmalıdır.")
            return

        if remove_admin_id == OWNER_ID:
            bot.reply_to(message, "❌ Kurucuyu admin listesinden çıkaramazsınız.")
            return

        if remove_admin_id not in ADMIN_USERS:
            bot.reply_to(message, "❌ Bu kullanıcı admin değil.")
            return

        ADMIN_USERS.remove(remove_admin_id)
        save_admin_users()  # Admin listesini kaydet
        bot.reply_to(message, f"✅ Kullanıcı {remove_admin_id} admin listesinden çıkarıldı.\n\n📝 Admin listesi kaydedildi.")
    except ValueError:
        bot.reply_to(message, "❌ Geçersiz kullanıcı ID. Lütfen sayısal bir değer girin.")
    except Exception as e:
        bot.reply_to(message, f"❌ Bir hata oluştu: {str(e)}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.chat.id
    if user_id not in ADMIN_USERS:
        bot.reply_to(message, "❌ Bu komut sadece adminler için geçerlidir.")
        return

    total_users = len(user_data)
    total_searches = len(search_results)
    cache_size = len(search_cache)
    admin_count = len(ADMIN_USERS)

    stats_text = f"""📊 *Bot İstatistikleri*

👥 Toplam Kullanıcı: {total_users}
🔍 Aktif Aramalar: {total_searches}
⚡ Önbellek Boyutu: {cache_size}
👑 Admin Sayısı: {admin_count}

💾 Geçici Dosyalar: {len(list(TEMP_DIR.glob('*')))}"""

    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = message.chat.id
    if user_id not in ADMIN_USERS:
        bot.reply_to(message, "❌ Bu komut sadece adminler için geçerlidir.")
        return

    broadcast_text = message.text.replace('/broadcast', '').strip()
    if not broadcast_text:
        bot.reply_to(message, "❌ Kullanım: /broadcast [mesaj]\n\nÖrnek: /broadcast Merhaba! Bot güncellendi.")
        return

    # Kullanıcı listesini al
    target_users = list(user_data.keys())
    if not target_users:
        bot.reply_to(message, "❌ Gönderilecek kullanıcı bulunamadı.")
        return

    # Broadcast başlatma mesajı
    progress_msg = bot.reply_to(message, f"📢 Broadcast başlatılıyor...\n👥 Toplam kullanıcı: {len(target_users)}")

    sent_count = 0
    failed_count = 0
    blocked_count = 0
    error_details = []

    # Her kullanıcıya mesaj gönder
    for i, target_user_id in enumerate(target_users, 1):
        try:
            bot.send_message(target_user_id, f"📢 *Duyuru:*\n\n{broadcast_text}", parse_mode='Markdown')
            sent_count += 1

            # Her 10 kullanıcıda bir ilerleme güncellemesi
            if i % 10 == 0:
                try:
                    bot.edit_message_text(
                        f"📢 Broadcast devam ediyor...\n📤 Gönderildi: {sent_count}\n❌ Başarısız: {failed_count}\n👥 İşlenen: {i}/{len(target_users)}",
                        message.chat.id,
                        progress_msg.message_id
                    )
                except:
                    pass  # İlerleme mesajı güncellenemezse devam et

        except telebot.apihelper.ApiTelegramException as e:
            failed_count += 1
            if "bot was blocked by the user" in str(e).lower():
                blocked_count += 1
            else:
                error_details.append(f"Kullanıcı {target_user_id}: {str(e)}")
        except Exception as e:
            failed_count += 1
            error_details.append(f"Kullanıcı {target_user_id}: {str(e)}")

    # Sonuç mesajı
    result_text = f"""✅ *Broadcast Tamamlandı!*

📤 *Başarıyla Gönderildi:* {sent_count}
❌ *Başarısız:* {failed_count}"""

    if blocked_count > 0:
        result_text += f"\n🚫 *Botu Engelleyen:* {blocked_count}"

    if error_details:
        result_text += f"\n⚠️ *Hata Detayları:*\n" + "\n".join(error_details[:5])  # İlk 5 hatayı göster
        if len(error_details) > 5:
            result_text += f"\n... ve {len(error_details) - 5} hata daha"

    try:
        bot.edit_message_text(result_text, message.chat.id, progress_msg.message_id, parse_mode='Markdown')
    except:
        bot.reply_to(message, result_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data

    # Premium kullanıcı kontrolü (örnek, basit liste)
    premium_users = {123456789}  # Buraya premium kullanıcı ID'leri eklenecek

    if data.startswith('bitrate_'):
        bitrate = data.split('_')[1] + 'k'
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['bitrate'] = bitrate
        bot.answer_callback_query(call.id, f"Ses kalitesi {bitrate} olarak ayarlandı!")
        bot.edit_message_text(f"✅ Ses kalitesi *{bitrate}* olarak güncellendi!",
                             user_id, call.message.message_id, parse_mode='Markdown')

    elif data.startswith('download_'):
        video_id = data.split('_')[1]
        bitrate = user_data.get(user_id, {}).get('bitrate', '320k')

        try:
            bot.answer_callback_query(call.id, "⏳ Şarkı indiriliyor...")

            mp3_file = indir_ve_donustur(video_id, bitrate)

            # Şarkı bilgilerini al
            results = search_results.get(str(user_id), [])
            song_info = next((item for item in results if item['id'] == video_id), None)

            caption = f"🎵 {song_info['title']}" if song_info else "🎵 İndirilen Şarkı"
            if song_info and 'duration' in song_info:
                caption += f"\n⏱️ {format_sure(song_info['duration'])}"

            # Oynatma kontrol butonları (premium kullanıcılar için)
            markup = telebot.types.InlineKeyboardMarkup()
            if user_id in premium_users:
                markup.row(
                    telebot.types.InlineKeyboardButton("⏮️", callback_data=f"prev_{video_id}"),
                    telebot.types.InlineKeyboardButton("▶️", callback_data=f"play_{video_id}"),
                    telebot.types.InlineKeyboardButton("⏭️", callback_data=f"next_{video_id}"),
                    telebot.types.InlineKeyboardButton("⏹️", callback_data=f"stop_{video_id}")
                )
                markup.row(
                    telebot.types.InlineKeyboardButton("✅ Listeye Ekle", callback_data=f"addlist_{video_id}"),
                    telebot.types.InlineKeyboardButton("🔮 Kontrol Paneli", callback_data=f"controlpanel_{video_id}")
                )

            try:
                with open(mp3_file, 'rb') as audio:
                    bot.send_audio(user_id, audio, caption=caption, reply_markup=markup, parse_mode='Markdown')
            except Exception as e:
                print(f"Dosya gönderilirken hata oluştu: {e}")

            try:
                mp3_file.unlink()
            except Exception as e:
                print(f"Dosya silinirken hata oluştu: {e}")

        except Exception as e:
            bot.answer_callback_query(call.id, "❌ İndirme hatası!")
            bot.send_message(user_id, f"❌ Hata: {str(e)}")

    elif data.startswith('play_'):
        # TODO: Oynatma başlatma işlemi (premium)
        bot.answer_callback_query(call.id, "▶️ Oynatma başlatıldı (simüle).")

    elif data.startswith('next_'):
        # TODO: Sonraki şarkıya geçiş işlemi (premium)
        bot.answer_callback_query(call.id, "⏭️ Sonraki şarkıya geçildi (simüle).")

    elif data.startswith('stop_'):
        # TODO: Oynatmayı durdurma işlemi (premium)
        bot.answer_callback_query(call.id, "⏹️ Oynatma durduruldu (simüle).")

    # Admin callback'leri
    elif data == 'admin_list':
        if user_id not in ADMIN_USERS:
            bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
            return

        admin_list = "\n".join([f"• {admin_id}" for admin_id in ADMIN_USERS])
        bot.answer_callback_query(call.id, "Admin listesi gönderildi.")
        bot.send_message(user_id, f"👑 *Admin Listesi:*\n\n{admin_list}", parse_mode='Markdown')

    elif data == 'admin_stats':
        if user_id not in ADMIN_USERS:
            bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
            return

        total_users = len(user_data)
        total_searches = len(search_results)
        cache_size = len(search_cache)
        admin_count = len(ADMIN_USERS)

        stats_text = f"""📊 *Bot İstatistikleri*

👥 Toplam Kullanıcı: {total_users}
🔍 Aktif Aramalar: {total_searches}
⚡ Önbellek Boyutu: {cache_size}
👑 Admin Sayısı: {admin_count}

💾 Geçici Dosyalar: {len(list(TEMP_DIR.glob('*')))}"""

        bot.answer_callback_query(call.id, "İstatistikler gönderildi.")
        bot.send_message(user_id, stats_text, parse_mode='Markdown')

    elif data == 'admin_broadcast':
        if user_id not in ADMIN_USERS:
            bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
            return

        bot.answer_callback_query(call.id, "Broadcast mesajı yazın.")
        bot.send_message(user_id, "📢 *Broadcast Modu*\n\nGöndermek istediğiniz mesajı yazın:", parse_mode='Markdown')

    elif data == 'admin_clear_cache':
        if user_id not in ADMIN_USERS:
            bot.answer_callback_query(call.id, "❌ Yetkisiz erişim!")
            return

        cache_count = len(search_cache)
        search_cache.clear()
        bot.answer_callback_query(call.id, f"Önbellek temizlendi! ({cache_count} giriş)")
        bot.send_message(user_id, f"✅ Önbellek temizlendi!\n🗑️ Temizlenen giriş sayısı: {cache_count}")

@bot.message_handler(func=lambda m: True)
def handle_query(message):
    user_id = message.chat.id
    query = message.text.strip()

    if not query:
        bot.reply_to(message, "❌ Lütfen bir şarkı adı veya sanatçı ismi yazın.")
        return

    try:
        bot.reply_to(message, "🔍 YouTube'da aranıyor...")

        # Arama yap
        results = arama_yap(query, 5)

        if not results:
            bot.reply_to(message, "❌ Arama sonucu bulunamadı. Farklı bir terim deneyin.")
            return

        # Sonuçları sakla
        search_results[str(user_id)] = results

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
        bot.reply_to(message, f"❌ Bir hata oluştu:\n{str(e)}")

# --- SUNUCUYU BAŞLAT ---
if __name__ == "__main__":
    print("🚀 ZB MUSIC Bot başlatılıyor...")
    try:
        # Polling modunda çalıştır
        print("📡 Bot polling modunda çalışıyor...")
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"❌ Bot başlatılırken hata oluştu: {e}")
