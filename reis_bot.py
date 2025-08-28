import os
import telebot
from flask import Flask, request

# Bot ve sunucu yapılandırması
BOT_TOKEN = os.getenv("BOT_TOKEN", "test_token")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
search_results = {}

# Yardımcı fonksiyonlar
def format_sure(saniye):
    dakika = int(saniye) // 60
    saniye = int(saniye) % 60
    return f"{dakika:02d}:{saniye:02d}"

def arama_yap(query, max_results=5):
    # YouTube API veya alternatif arama mantığı burada olmalı
    return []

# Callback handler
@bot.callback_query_handler(func=lambda call: call.data.startswith("download_"))
def handle_download(call):
    user_id = call.message.chat.id
    video_id = call.data.split("_")[1]
    song_info = {"title": "Örnek Şarkı", "duration": 215}
    mp3_file = "indirilen_sarki.mp3"

    try:
        caption = f"🎵 {song_info['title']}" if song_info else "🎵 İndirilen Şarkı"
        if song_info and 'duration' in song_info:
            caption += f"\n⏱️ {format_sure(song_info['duration'])}"

        with open(mp3_file, 'rb') as audio:
            bot.send_audio(user_id, audio, caption=caption, parse_mode='Markdown')

        os.remove(mp3_file)
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ İndirme hatası!")
        bot.send_message(user_id, f"❌ Hata: {str(e)}")

# Mesaj handler
@bot.message_handler(func=lambda m: True)
def handle_query(message):
    user_id = message.chat.id
    query = message.text.strip()

    if not query:
        bot.reply_to(message, "❌ Lütfen bir şarkı adı veya sanatçı ismi yazın.")
        return

    try:
        bot.reply_to(message, "🔍 YouTube'da aranıyor...")
        results = arama_yap(query, 5)

        if not results:
            bot.reply_to(message, "❌ Arama sonucu bulunamadı. Farklı bir terim deneyin.")
            return

        search_results[str(user_id)] = results

        markup = telebot.types.InlineKeyboardMarkup()
        for i, result in enumerate(results[:5], 1):
            title = result.get('title', 'Bilinmeyen')
            duration = format_sure(result.get('duration', 0)) if result.get('duration') else 'Bilinmiyor'
            markup.row(telebot.types.InlineKeyboardButton(
                f"{i}. {title[:30]}... ({duration})",
                callback_data=f"download_{result['id']}"
            ))

        bot.send_message(
            user_id,
            f"🎵 *Arama Sonuçları:*\n\nAramak için: `{query}`\n\nİndirmek istediğiniz şarkıyı seçin:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        bot.reply_to(message, f"❌ Bir hata oluştu:\n{str(e)}")

# --- SUNUCUYU BAŞLAT ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    if BOT_TOKEN == "test_token":
        print("🧪 Test modunda çalışıyor... Telegram bağlantısı yok.")
        print("Bot fonksiyonları test edilebilir durumda.")
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        print("🚀 ZB MUSIC Bot başlatılıyor (Polling modunda)...")
        try:
            bot.remove_webhook()
            print("🤖 Bot polling modunda çalışıyor. Mesajları dinliyor...")
            bot.infinity_polling()
        except Exception as e:
            print(f"❌ Telegram bağlantı hatası: {e}")
            print("🌐 Flask sunucusu başlatılıyor...")
            try:
                app.run(host='0.0.0.0', port=port, debug=True)
            except Exception as e:
                print(f"❌ Flask sunucusu başlatılamadı: {e}")
