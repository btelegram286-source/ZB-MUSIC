import os
import uuid
import telebot
import yt_dlp
import ffmpeg
import logging
import requests
import json
from flask import Flask, request, abort
from pathlib import Path

# --- AYARLAR ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY")
WEBHOOK_HOST = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app-name.onrender.com')
WEBHOOK_PORT = os.environ.get('PORT', 5000)
WEBHOOK_LISTEN = '0.0.0.0'
SOUNDCLOUD_CLIENT_ID = os.environ.get('SOUNDCLOUD_CLIENT_ID', 'YOUR_SOUNDCLOUD_CLIENT_ID')

bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("temp_music")
TEMP_DIR.mkdir(exist_ok=True)

# Flask app
app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)

# --- WEBHOOK HANDLERS ---
@app.route('/')
def home():
    return "🎵 ZB MUSIC Bot Webhook Server - Çalışıyor!"

@app.route('/ping')
def ping():
    return "pong"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

# --- MÜZİK İNDİRME VE DÖNÜŞTÜRME ---
def get_soundcloud_track(query):
    """SoundCloud'da arama yaparak track URL'sini bulur"""
    try:
        search_url = f"https://api-v2.soundcloud.com/search/tracks?q={query.replace(' ', '+')}&client_id={SOUNDCLOUD_CLIENT_ID}&limit=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('collection') and len(data['collection']) > 0:
                track = data['collection'][0]
                return track.get('permalink_url')  # Track URL'sini döndür
    except Exception as e:
        logging.error(f"SoundCloud arama hatası: {e}")
    
    return None

def get_youtube_video_id(query):
    """YouTube'da arama yaparak video URL'sini bulur"""
    try:
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            import re
            video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', response.text)
            if video_ids:
                return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        logging.error(f"YouTube arama hatası: {e}")
    
    return None

def indir_ve_donustur(query):
    unique_id = str(uuid.uuid4())
    mp3_path = TEMP_DIR / f"{unique_id}.mp3"

    # Önce YouTube'u dene (daha güvenilir)
    youtube_url = get_youtube_video_id(query)
    if youtube_url:
        wav_path = TEMP_DIR / f"{unique_id}.wav"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(wav_path.with_suffix('.%(ext)s')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])

            downloaded_file = next(TEMP_DIR.glob(f"{unique_id}.*"))
            
            ffmpeg.input(str(downloaded_file)).output(str(mp3_path), audio_bitrate='320k').run(overwrite_output=True, quiet=True)
            downloaded_file.unlink()

            return mp3_path
            
        except Exception as e:
            # Hata durumunda temizlik
            for temp_file in TEMP_DIR.glob(f"{unique_id}.*"):
                try:
                    temp_file.unlink()
                except:
                    pass
            raise e

    raise Exception("Şarkı bulunamadı")

# --- BOT KOMUTLARI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🎶 Selam reis! Şarkı ismini gönder, sana MP3 olarak araç formatında yollayayım.")

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    bot.reply_to(message, f"Chat ID'niz: {message.chat.id}")

@bot.message_handler(commands=['status'])
def send_status(message):
    bot.reply_to(message, "✅ Bot çalışıyor! Webhook modunda.")

@bot.message_handler(func=lambda m: True)
def handle_query(message):
    try:
        if len(message.text) > 100:
            bot.reply_to(message, "❌ Şarkı ismi çok uzun, maksimum 100 karakter.")
            return
            
        bot.reply_to(message, "🔍 Müzik aranıyor ve indiriliyor...")
        mp3_file = indir_ve_donustur(message.text)
        
        with open(mp3_file, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=message.text)
        
        mp3_file.unlink()
        
    except Exception as e:
        bot.reply_to(message, f"❌ Bir hata oluştu reis:\n{str(e)}")
        logging.error(f"Hata: {e}")

# --- WEBHOOK KURULUMU ---
def set_webhook():
    webhook_url = f"{WEBHOOK_HOST}/{BOT_TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to: {webhook_url}")

# --- ÇALIŞTIR ---
if __name__ == "__main__":
    # Local development için polling modu
    # Render deploy için webhook modu
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--webhook':
        set_webhook()
        app.run(
            host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            debug=False
        )
    else:
        # Polling modu (local test için)
        print("🤖 Polling modunda başlatılıyor...")
        bot.remove_webhook()
        bot.infinity_polling()
