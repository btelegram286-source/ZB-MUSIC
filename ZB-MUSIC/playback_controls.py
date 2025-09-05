"""
Playback Kontrol Fonksiyonları
Ana bot dosyasında kullanılmak üzere playback kontrol fonksiyonları
"""
import time
from typing import Dict, List, Optional
import telebot

def handle_playback_callback(bot: telebot.TeleBot, call, user_id: int, data: str,
                           now_playing: Dict, playback_state: Dict, user_queues: Dict,
                           music_library: Dict, premium_users: set):
    """Playback ile ilgili callback'ları işle"""

    if data.startswith('play_'):
        # Gerçek oynatma başlatma işlemi
        video_id = data.split('_')[1]
        if user_id not in premium_users:
            bot.answer_callback_query(call.id, "❌ Bu özellik premium kullanıcılar için")
            return

        # Şu anda çalan şarkıyı ayarla
        now_playing[user_id] = {
            'video_id': video_id,
            'title': music_library.get(video_id, {}).get('title', 'Bilinmeyen'),
            'start_time': time.time(),
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
        bot.send_message(user_id, f"▶️ *Şu Anda Çalıyor:*\n🎵 {song_title}\n\nSes seviyesi: 80%\nTekrar modu: off\nKarıştır: Kapalı",
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
                'start_time': time.time(),
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

        bot.send_message(user_id, f"🔊 *Ses Seviyesi*\n\nMevcut: 80%\n\nYeni seviye seçin:",
                        reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id, "🔊 Ses kontrolü açıldı")

    elif data.startswith('vol_'):
        # Ses seviyesini ayarla
        vol_level = float(data.split('_')[1])
        bot.answer_callback_query(call.id, f"🔊 Ses seviyesi {vol_level*100:.0f}% olarak ayarlandı")
        bot.send_message(user_id, f"✅ Ses seviyesi *{vol_level*100:.0f}%* olarak güncellendi!", parse_mode='Markdown')

    elif data.startswith('repeat_'):
        # Tekrar modu değiştir
        bot.answer_callback_query(call.id, f"🔁 Tekrar modu: one")
        bot.send_message(user_id, f"✅ Tekrar modu: *one*", parse_mode='Markdown')

    elif data.startswith('shuffle_'):
        # Karıştırma modu değiştir
        bot.answer_callback_query(call.id, f"🔀 Karıştırma: Açık")
        bot.send_message(user_id, f"✅ Karıştırma modu: *Açık*", parse_mode='Markdown")

def create_playback_markup(video_id: str) -> telebot.types.InlineKeyboardMarkup:
    """Playback kontrol butonları için markup oluştur"""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("▶️ Başlat", callback_data=f"play_{video_id}"),
        telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data=f"next_{video_id}"),
        telebot.types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{video_id}")
    )
    return markup
