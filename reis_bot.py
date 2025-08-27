import os
import uuid
import telebot
import yt_dlp
import ffmpeg
import logging
from flask import Flask, request, abort
from pathlib import Path

# --- AYARLAR ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY")
WEBHOOK_HOST = os.environ.get('WEBHOOK_HOST', 'https://your-app-name.herokuapp.com')
WEBHOOK_PORT = os.environ.get('PORT', 5000)
WEBHOOK_LISTEN = '0.0.0.0'

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
def indir_ve_donustur(query):
    unique_id = str(uuid.uuid4())
    video_url = f"ytsearch1:{query}"
    mp3_path = TEMP_DIR / f"{unique_id}.mp3"
    wav_path = TEMP_DIR / f"{unique_id}.wav"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(wav_path.with_suffix('.%(ext)s')),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    downloaded_file = next(TEMP_DIR.glob(f"{unique_id}.*"))
    
    ffmpeg.input(str(downloaded_file)).output(str(mp3_path), audio_bitrate='320k').run(overwrite_output=True, quiet=True)
    downloaded_file.unlink()

    return mp3_path

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
    set_webhook()
    app.run(
        host=WEBHOOK_LISTEN,
        port=WEBHOOK_PORT,
        debug=False
    )
