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
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN ortam değişkeni ayarlanmamış! Lütfen bot tokenını ayarlayın.")
bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("ZB_MUSIC")
TEMP_DIR.mkdir(exist_ok=True)
# Kullanıcı verileri ve arama sonuçları için geçici depolama
user_data: Dict[int, Dict] = {}
search_results: Dict[str, List[Dict]] = {}

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

def indir_ve_donustur(video_id: str, bitrate: str = '320k') -> Path:
    """Belirli bir video ID'sini indir ve MP3'e dönüştür (gelişmiş versiyon)"""
    unique_id = str(uuid.uuid4())
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    mp3_path = TEMP_DIR / f"{unique_id}.mp3"
    temp_path = TEMP_DIR / f"{unique_id}"

    # Çerezleri environment variable'dan al
    yt_cookies = os.environ.get('YT_COOKIES', '')
    
    # İndirme seçenekleri - önce normal, sonra Android client ile dene
    ydl_opts_list = [
        # 1. Deneme: Normal web client + çerezler
        {
            'format': 'bestaudio/best',
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
            'format': 'bestaudio/best',
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
            'user_agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
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
            print(f"⏳ İndirme denemesi {i}/2: {ydl_opts['extractor_args']['youtube']['player_client'][0]} client")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            downloaded_file = next(TEMP_DIR.glob(f"{unique_id}.*"))
            ffmpeg.input(str(downloaded_file)).output(str(mp3_path), audio_bitrate=bitrate).run(overwrite_output=True)
            downloaded_file.unlink()

            # Temizlik: Geçici cookies.txt dosyasını sil
            if yt_cookies and os.path.exists('cookies.txt'):
                os.remove('cookies.txt')
                
            return mp3_path

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
    help_text = """❓ *Yardım Menüsü*

🔍 *Arama Yapma:*
Sadece şarkı adı veya sanatçı ismi yazın. Örnek:
• `tarkan kiss kiss`
• `müslüm gürses affet`
• `sezen aksu şarkıları`

⚙️ *Ses Kalitesi:*
/ayarlar komutu ile ses kalitesini değiştirebilirsiniz.

📊 *Limitler:*
• Günlük 20 şarkı indirme limiti
• Maximum 10 dakika şarkı süresi

🚨 *Sorun Giderme:*
Eğer şarkı indirilemezse, farklı bir arama terimi deneyin.

📞 *Destek:*
Sorunlarınız için @btelegram286"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

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
            mp3_file = indir_ve_donustur(video_id, bitrate)
            
            # Şarkı bilgilerini al
            results = search_results.get(str(user_id), [])
            song_info = next((item for item in results if item['id'] == video_id), None)
            
            caption = f"🎵 {song_info['title']}" if song_info else "🎵 İndirilen Şarkı"
            if song_info and 'duration' in song_info:
                caption += f"\n⏱️ {format_sure(song_info['duration'])}"
            
            with open(mp3_file, 'rb') as audio:
                bot.send_audio(user_id, audio, caption=caption, parse_mode='Markdown')
            
            mp3_file.unlink()
            
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ İndirme hatası!")
            bot.send_message(user_id, f"❌ Hata: {str(e)}")

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
    # Test modunda mı kontrol et
    if BOT_TOKEN == "test_token":
        print("🧪 Test modunda çalışıyor... Telegram bağlantısı yok.")
        print("Bot fonksiyonları test edilebilir durumda.")
        # Flask sunucusunu başlat
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("🚀 ZB MUSIC Bot başlatılıyor (Polling modunda)...")
        try:
            bot.remove_webhook()
            print("🤖 Bot polling modunda çalışıyor. Mesajları dinliyor...")
            bot.infinity_polling()
        except Exception as e:
            print(f"❌ Telegram bağlantı hatası: {e}")
            print("🌐 Flask sunucusu başlatılıyor...")
            app.run(host='0.0.0.0', port=5000, debug=True)
