import os
import uuid
import telebot
import yt_dlp
import ffmpeg
import subprocess
import requests
from flask import Flask
from threading import Thread

from pathlib import Path

# --- AYARLAR ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY")
bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("ZB_MUSIC")
TEMP_DIR.mkdir(exist_ok=True)

# Flask app for keeping the bot alive
app = Flask(__name__)

@app.route('/')
def home():
    return "ZB MUSIC Bot is running!"

@app.route('/ping')
def ping():
    return "pong"

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def run_bot():
    print("[REIS BOT] Başlatıldı...")
    bot.infinity_polling()

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
    
    ffmpeg.input(str(downloaded_file)).output(str(mp3_path), audio_bitrate='320k').run(overwrite_output=True)
    downloaded_file.unlink()

    return mp3_path

# --- BOT KOMUTU ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🎶 Selam reis! Şarkı ismini gönder, sana MP3 olarak araç formatında yollayayım.")

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    bot.reply_to(message, f"Chat ID'niz: {message.chat.id}")

@bot.message_handler(func=lambda m: True)
def handle_query(message):
    try:
        bot.reply_to(message, "🔍 Müzik aranıyor ve indiriliyor...")
        mp3_file = indir_ve_donustur(message.text)
        bot.send_audio(message.chat.id, open(mp3_file, 'rb'))
        mp3_file.unlink()
    except Exception as e:
        bot.reply_to(message, f"❌ Bir hata oluştu reis:\n{str(e)}")

# --- ÇALIŞTIR ---
if __name__ == "__main__":
    print("Starting ZB MUSIC Bot with Flask server...")
    
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the bot
    run_bot()
