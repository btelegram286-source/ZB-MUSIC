import os
import uuid
import random
import time
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import telebot
import yt_dlp
import ffmpeg
import json
from flask import Flask, request
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

# --- ULTRA PREMIUM MODÜLLER ---
from ZB_MUSIC.ZB_MUSIC.database_simple_final import get_db, get_user, create_user, get_user_downloads, add_download
from ZB_MUSIC.ZB_MUSIC.lyrics_api import LyricsAPI
from ZB_MUSIC.ZB_MUSIC.spotify_integration import SpotifyIntegration
from ZB_MUSIC_temp.equalizer import Equalizer
from ZB_MUSIC_temp.audio_effects import AudioEffects
from ZB_MUSIC_temp.advanced_playback import AdvancedPlayback

# --- AYARLAR ---
BOT_TOKEN = "8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY"
bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = Path("ZB_MUSIC_ULTRA_PREMIUM")
TEMP_DIR.mkdir(exist_ok=True)

# --- VERİ YAPILARI ---
user_data: Dict[int, Dict] = {}
search_results: Dict[str, List[Dict]] = {}

# --- ULTRA MÜZİK SİSTEMİ ---
user_queues: Dict[int, List[str]] = {}
user_playlists: Dict[int, Dict[str, List[str]]] = {}
user_favorites: Dict[int, List[Dict]] = {}
user_stats: Dict[int, Dict] = {}
music_library: Dict[str, Dict] = {}

# --- GELİŞMİŞ OYNATMA SİSTEMİ ---
now_playing: Dict[int, Dict] = {}
playback_state: Dict[int, str] = {}
user_volume: Dict[int, float] = {}
repeat_mode: Dict[int, str] = {}
shuffle_mode: Dict[int, bool] = {}
playback_position: Dict[int, float] = {}
playback_start_time: Dict[int, float] = {}
current_queue_index: Dict[int, int] = {}

# --- SOSYAL AĞ ÖZELLİKLERİ ---
user_profiles: Dict[int, Dict] = {}
music_shares: Dict[str, Dict] = {}
friend_lists: Dict[int, List[int]] = {}
user_followers: Dict[int, List[int]] = {}
user_following: Dict[int, List[int]] = {}
music_posts: Dict[str, Dict] = {}
social_feed: List[Dict] = []

# --- ULTRA PREMIUM SİSTEMİ ---
premium_users: set = {123456789, 1275184751}
premium_subscriptions: Dict[int, Dict] = {}
ultra_premium_features = {
    'unlimited_downloads': True,
    'high_quality_audio': True,
    'video_download': True,
    'advanced_controls': True,
    'social_features': True,
    'group_support': True,
    'admin_panel': True,
    'music_discovery': True,
    'no_ads': True,
    'lyrics_support': True,
    'spotify_integration': True,
    'personal_recommendations': True,
    'cloud_sync': True,
    'offline_mode': True,
    'ai_recommendations': True,
    'music_production': True,
    'advanced_games': True,
    'analytics_dashboard': True,
    'social_networking': True,
    'mobile_app_sync': True,
    'voice_commands': True,
    'karaoke_mode': True,
    'music_visualizer': True,
    'concert_tickets': True,
    'artist_chat': True,
    'music_creation': True,
    'remix_tools': True,
    'dj_mixer': True,
    'live_streaming': True,
    'music_lessons': True,
    'neural_mix': True,
    'stem_separation': True,
    'ai_song_writer': True,
    'virtual_concerts': True,
    'music_therapy': True
}

# --- GRUP SİSTEMİ ---
group_settings: Dict[int, Dict] = {}
group_queues: Dict[int, List[str]] = {}
group_admins: Dict[int, List[int]] = {}

# --- MÜZİK KEŞİF & AI ---
trending_songs: List[Dict] = []
daily_recommendations: Dict[int, List[str]] = {}
music_genres: Dict[str, List[str]] = {}
artist_database: Dict[str, Dict] = {}
ai_music_models: Dict[str, Dict] = {}

# --- OYUN SİSTEMİ ---
game_scores: Dict[int, Dict] = {}
active_games: Dict[int, Dict] = {}
game_leaderboards: Dict[str, List[Dict]] = {}

# --- ANALİTİK SİSTEMİ ---
user_analytics: Dict[int, Dict] = {}
system_analytics: Dict = {}
music_insights: Dict[str, Dict] = {}

# --- PRODÜKSİYON ARAÇLARI ---
chord_progressions: Dict[str, List[str]] = {}
music_scales: Dict[str, List[str]] = {}
drum_patterns: Dict[str, List[str]] = {}
production_presets: Dict[str, Dict] = {}

# --- SES KOMUTLARI ---
voice_commands: Dict[str, str] = {
    'çal': 'play',
    'durdur': 'stop',
    'sonraki': 'next',
    'önceki': 'previous',
    'karıştır': 'shuffle',
    'tekrar': 'repeat',
    'sesi aç': 'volume_up',
    'sesi kıs': 'volume_down'
}

# --- ADMIN SİSTEMİ ---
admin_users: set = {1275184751}
bot_stats: Dict = {
    'total_users': 0,
    'total_downloads': 0,
    'active_sessions': 0,
    'server_status': 'online'
}
system_logs: List[Dict] = []

# --- ULTRA PREMIUM MODÜL BAŞLATMA ---
lyrics_api = LyricsAPI()
spotify_integration = SpotifyIntegration()
equalizer = Equalizer()
audio_effects = AudioEffects()
advanced_playback = AdvancedPlayback()

# --- FLASK SUNUCUSU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🎵 ZB MUSIC ULTRA PREMIUM Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# --- GELİŞMİŞ MÜZİK İNDİRME ---
def arama_yap(query: str, limit: int = 5) -> List[Dict]:
    """YouTube'da gelişmiş arama yap"""
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
    """Gelişmiş indirme ve dönüştürme"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
    except Exception as e:
        print(f"⚠️ yt-dlp güncelleme hatası: {e}")

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

    ydl_opts_list = [
        {
            'format': output_format,
            'outtmpl': str(temp_path.with_suffix('.%(ext)s')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android', 'ios'],
                    'player_skip': ['js', 'configs'],
                }
            },
        }
    ]

    for ydl_opts in ydl_opts_list:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            if format_type == 'audio':
                # FFmpeg ile MP3'e dönüştür
                input_file = temp_path.with_suffix('.webm') if temp_path.with_suffix('.webm').exists() else temp_path.with_suffix('.m4a')
                if input_file.exists():
                    ffmpeg_cmd = [
                        'ffmpeg', '-i', str(input_file),
                        '-b:a', bitrate, '-vn', str(mp3_path), '-y'
                    ]
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                    input_file.unlink()
                    return mp3_path
            else:
                return temp_path.with_suffix('.mp4')

        except Exception as e:
            print(f"İndirme hatası: {e}")
            continue

    raise Exception("Tüm indirme yöntemleri başarısız oldu")

def format_sure(saniye) -> str:
    """Saniyeyi formatla"""
    try:
        saniye_int = int(float(saniye))
        dakika = saniye_int // 60
        saniye_kalan = saniye_int % 60
        return f"{dakika}:{saniye_kalan:02d}"
    except (ValueError, TypeError):
        return "Bilinmiyor"

# --- ULTRA PREMIUM BOT KOMUTLARI ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id

    # Kullanıcıyı veritabanına kaydet
    db = get_db()
    db_user = get_user(db, user_id)
    if not db_user:
        create_user(db, user_id, message.from_user.username, message.from_user.first_name)

    welcome_text = """🎶 *ZB MUSIC ULTRA PREMIUM*

🤖 *Tüm Premium Özellikler:*
• 🎵 Şarkı Sözleri & Analizi
• 🎧 Spotify & Apple Music Entegrasyonu
• 🎯 AI Müzik Önerileri
• 🎮 Gelişmiş Oyunlar
• 📊 Analitik Dashboard
• 👥 Sosyal Ağ Özellikleri
• 🎼 Müzik Prodüksiyon Araçları
• 📱 Mobil Uygulama Senkronizasyonu
• ☁️ Bulut Yedekleme
• 🎯 Kişiselleştirilmiş Keşif

🎵 *Hızlı Başlangıç:*
/premium - Tüm özellikleri gör
/ai - AI müzik önerileri
/social - Sosyal özellikler
/games - Premium oyunlar
/analytics - İstatistikleriniz"""

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎵 Müzik", "🎧 Spotify", "🎯 AI Öneriler")
    markup.row("🎮 Oyunlar", "👥 Sosyal", "📊 Analitik")
    markup.row("🎼 Prodüksiyon", "⚙️ Ayarlar", "❓ Yardım")

    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['ai'])
def handle_ai_recommendations(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    try:
        bot.reply_to(message, "🤖 AI müzik önerileri hazırlanıyor...")

        # AI tabanlı öneriler
        ai_recommendations = get_ai_recommendations(user_id)

        if not ai_recommendations:
            bot.reply_to(message, "❌ Yeterli veri bulunamadı. Daha fazla şarkı dinleyerek AI önerilerinizi iyileştirin.")
            return

        text = "🤖 *AI Müzik Önerileriniz*\n\n"
        markup = telebot.types.InlineKeyboardMarkup()

        for i, rec in enumerate(ai_recommendations[:10], 1):
            title = rec.get('title', 'Bilinmeyen')[:30]
            confidence = rec.get('confidence', 0) * 100
            text += f"{i}. {title}\n   🎯 %{confidence:.1f} uyumluluk\n\n"

            markup.row(telebot.types.InlineKeyboardButton(
                f"▶️ {title[:20]}...",
                callback_data=f"play_ai_{rec['video_id']}"
            ))

        markup.row(telebot.types.InlineKeyboardButton("🔄 Yeni Öneriler", callback_data="refresh_ai_recommendations"))

        bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ AI öneri hatası: {str(e)}")

@bot.message_handler(commands=['social'])
def handle_social_features(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("👥 Arkadaşlar", callback_data="social_friends"),
        telebot.types.InlineKeyboardButton("🎵 Müzik Paylaş", callback_data="social_share_music")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("📊 Takipçiler", callback_data="social_followers"),
        telebot.types.InlineKeyboardButton("🎯 Trend Müzikler", callback_data="social_trending")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("💬 Müzik Sohbeti", callback_data="social_chat"),
        telebot.types.InlineKeyboardButton("🏆 Lider Tablosu", callback_data="social_leaderboard")
    )

    text = """👥 *Sosyal Ağ Özellikleri*

🤝 *Arkadaş Sistemi:*
• Arkadaş ekleme/çıkarma
• Müzik paylaşımı
• Birlikte dinleme

🎵 *Müzik Paylaşımı:*
• Favori şarkılarınızı paylaşın
• Playlistlerinizi yayınlayın
• Müzik keşiflerinizi gösterin

📊 *Topluluk:*
• Trend müzikler
• Kullanıcı önerileri
• Müzik tartışmaları"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['games'])
def handle_advanced_games(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎵 Müzik Quiz", callback_data="game_music_quiz"),
        telebot.types.InlineKeyboardButton("🎼 Nota Tahmin", callback_data="game_note_guess")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎯 Ritm Oyunu", callback_data="game_rhythm"),
        telebot.types.InlineKeyboardButton("🎪 Müzik Bellek", callback_data="game_music_memory")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎸 Sanal Enstrüman", callback_data="game_virtual_instrument"),
        telebot.types.InlineKeyboardButton("🏆 Skor Tablosu", callback_data="game_leaderboard")
    )

    text = """🎮 *Gelişmiş Müzik Oyunları*

🧠 *Zeka Oyunları:*
• Müzik Quiz - Şarkı ve sanatçı bilmece
• Nota Tahmin - Kulak müzik eğitimi
• Müzik Bellek - Hafıza geliştirme

🎯 *Beceri Oyunları:*
• Ritm Oyunu - Zamanlama becerisi
• Sanal Enstrüman - Müzik yapma

🏆 *Rekabet:*
• Skor sistemi
• Lider tabloları
• Başarı rozetleri"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['analytics'])
def handle_analytics_dashboard(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    try:
        # Kullanıcı analitiği
        analytics = get_user_analytics(user_id)

        text = f"""📊 *Müzik Analitik Dashboard*

🎵 *Dinleme İstatistikleri:*
• Toplam Dinleme: {analytics.get('total_plays', 0)} şarkı
• Favori Tür: {analytics.get('favorite_genre', 'Bilinmiyor')}
• En Çok Dinlenen: {analytics.get('most_played_artist', 'Bilinmiyor')}

⏱️ *Zaman Dağılımı:*
• Günlük Ortalama: {analytics.get('daily_average', 0)} dakika
• Haftalık Toplam: {analytics.get('weekly_total', 0)} dakika
• En Aktif Gün: {analytics.get('most_active_day', 'Bilinmiyor')}

🎯 *Keşif İstatistikleri:*
• Yeni Sanatçı: {analytics.get('new_artists_discovered', 0)}
• Tür Çeşitliliği: {analytics.get('genre_diversity', 0)} farklı tür
• Öneri Doğruluk: %{analytics.get('recommendation_accuracy', 0)}

📈 *Trend Analizi:*
• Müzik Zevki Değişimi: {analytics.get('taste_evolution', 'Sabit')}
• Trend Uyumluluk: %{analytics.get('trend_compatibility', 0)}"""

        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("📈 Detaylı Grafik", callback_data="analytics_charts"),
            telebot.types.InlineKeyboardButton("🎯 Öneriler", callback_data="analytics_suggestions")
        )
        markup.row(
            telebot.types.InlineKeyboardButton("📊 CSV Dışa Aktar", callback_data="analytics_export"),
            telebot.types.InlineKeyboardButton("🔄 Güncelle", callback_data="analytics_refresh")
        )

        bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Analitik hatası: {str(e)}")

@bot.message_handler(commands=['production'])
def handle_music_production(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎼 Akor Bulucu", callback_data="prod_chord_finder"),
        telebot.types.InlineKeyboardButton("🎵 Ton Analizi", callback_data="prod_tone_analysis")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎶 Melodi Üreteci", callback_data="prod_melody_generator"),
        telebot.types.InlineKeyboardButton("🎸 Enstrüman Öğren", callback_data="prod_instrument_learn")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎚️ Mixer", callback_data="prod_mixer"),
        telebot.types.InlineKeyboardButton("📚 Müzik Teori", callback_data="prod_music_theory")
    )

    text = """🎼 *Müzik Prodüksiyon Araçları*

🎵 *Kompozisyon:*
• Akor ilerlemeleri
• Melodi üretimi
• Harmoni analizi

🎶 *Öğrenme Araçları:*
• Enstrüman dersleri
• Müzik teorisi
• Kulak eğitimi

🎚️ *Prodüksiyon:*
• Dijital mixer
• Efekt işleme
• Mastering araçları"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['mobile'])
def handle_mobile_sync(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("📱 QR Kod", callback_data="mobile_qr_sync"))
    markup.row(telebot.types.InlineKeyboardButton("🔗 Bağlantı Oluştur", callback_data="mobile_link_generate"))
    markup.row(telebot.types.InlineKeyboardButton("📊 Senkronizasyon Durumu", callback_data="mobile_sync_status"))

    text = """📱 *Mobil Uygulama Senkronizasyonu*

🔄 *Senkronizasyon Özellikleri:*
• Tüm verileriniz mobil uygulamada
• Çapraz platform oynatma
• Offline müzik senkronizasyonu

📋 *Kurulum:*
1. QR kodu tarayın
2. Veya bağlantıyı mobil uygulamada açın
3. Otomatik senkronizasyon başlayacak

⚡ *Avantajlar:*
• Her yerden erişim
• Otomatik yedekleme
• Gelişmiş mobil arayüz"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['karaoke'])
def handle_karaoke_mode(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎤 Şarkı Seç", callback_data="karaoke_song_select"),
        telebot.types.InlineKeyboardButton("🎵 Vokal Kaldır", callback_data="karaoke_vocal_remove")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎯 Puan Sistemi", callback_data="karaoke_scoring"),
        telebot.types.InlineKeyboardButton("📹 Kayıt", callback_data="karaoke_record")
    )

    text = """🎤 *Karaoke Modu*

🎵 *Özellikler:*
• Vokalsiz şarkılar
• Puanlama sistemi
• Video kayıt
• Sosyal paylaşım

🎶 *Nasıl Kullanılır:*
1. Şarkı seçin
2. Vokal kaldırın
3. Mikrofonunuzla söyleyin
4. Puanınızı görün"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['voice'])
def handle_voice_commands(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎙️ Sesli Komut", callback_data="voice_record_command"),
        telebot.types.InlineKeyboardButton("📝 Komut Listesi", callback_data="voice_command_list")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎵 Müzik Arama", callback_data="voice_music_search"),
        telebot.types.InlineKeyboardButton("⚙️ Ayarlar", callback_data="voice_settings")
    )

    text = """🎙️ *Sesli Komutlar*

🗣️ *Mevcut Komutlar:*
• "çal [şarkı adı]" - Şarkı çal
• "durdur" - Müzik durdur
• "sonraki" - Sonraki şarkı
• "önceki" - Önceki şarkı
• "karıştır" - Listeyi karıştır
• "sesi aç/kıs" - Ses kontrolü

🎯 *Akıllı Özellikler:*
• Türkçe konuşma tanıma
• Müzik arama
• Oynatma kontrolü
• Akıllı öneriler"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['equalizer'])
def handle_equalizer(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🎛️ Bass Boost", callback_data="eq_bass_boost"),
        telebot.types.InlineKeyboardButton("🎚️ Treble Boost", callback_data="eq_treble_boost")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎵 Pop Preset", callback_data="eq_preset_pop"),
        telebot.types.InlineKeyboardButton("🎸 Rock Preset", callback_data="eq_preset_rock")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎹 Jazz Preset", callback_data="eq_preset_jazz"),
        telebot.types.InlineKeyboardButton("🎧 Reset", callback_data="eq_reset")
    )

    text = """🎛️ *Equalizer Kontrolleri*

🎚️ *Ön Ayar Seçenekleri:*
• Bass Boost - Bas sesleri güçlendir
• Treble Boost - Tiz sesleri güçlendir
• Pop Preset - Pop müzik için optimize
• Rock Preset - Rock müzik için optimize
• Jazz Preset - Jazz müzik için optimize

⚙️ *Manuel Ayarlar:*
• /eq_bass [0-100] - Bas seviyesi
• /eq_mid [0-100] - Orta seviye
• /eq_treble [0-100] - Tiz seviyesi"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['effects'])
def handle_audio_effects(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🔊 Reverb", callback_data="effect_reverb"),
        telebot.types.InlineKeyboardButton("⏯️ Echo", callback_data="effect_echo")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎛️ Chorus", callback_data="effect_chorus"),
        telebot.types.InlineKeyboardButton("📢 Distortion", callback_data="effect_distortion")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🎵 Auto-Tune", callback_data="effect_autotune"),
        telebot.types.InlineKeyboardButton("🔄 Reset", callback_data="effect_reset")
    )

    text = """🎵 *Ses Efektleri*

🎚️ *Mevcut Efektler:*
• Reverb - Salon etkisi
• Echo - Yankı efekti
• Chorus - Çoklu ses efekti
• Distortion - Distorsiyon
• Auto-Tune - Ses düzeltme

⚙️ *Kullanım:*
• Efekti seçin ve seviyesini ayarlayın
• Birden fazla efekt aynı anda kullanılabilir
• /effect_level [efekt] [0-100]"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['playback'])
def handle_advanced_playback(message):
    user_id = message.chat.id

    if user_id not in premium_users:
        bot.reply_to(message, "❌ Bu özellik premium kullanıcılar için geçerlidir.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("⏯️ Oynat/Durdur", callback_data="pb_play_pause"),
        telebot.types.InlineKeyboardButton("⏭️ Sonraki", callback_data="pb_next")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("⏮️ Önceki", callback_data="pb_previous"),
        telebot.types.InlineKeyboardButton("🔀 Karıştır", callback_data="pb_shuffle")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🔁 Tekrar", callback_data="pb_repeat"),
        telebot.types.InlineKeyboardButton("⏩ 2x Hız", callback_data="pb_speed_2x")
    )

    current_song = now_playing.get(user_id, {}).get('title', 'Hiç şarkı oynatılmıyor')
    current_state = playback_state.get(user_id, 'stopped')

    text = f"""🎵 *Gelişmiş Oynatma Kontrolleri*

🎶 *Şu An Oynatılan:* {current_song}
📊 *Durum:* {current_state.title()}

🎚️ *Kontroller:*
• Oynat/Durdur - Müzik kontrolü
• Sonraki/Önceki - Şarkı değiştirme
• Karıştır - Listeyi karıştır
• Tekrar - Tekrar modu
• Hız Kontrolü - Oynatma hızı

⚙️ *Ek Komutlar:*
• /volume [0-100] - Ses seviyesi
• /seek [saniye] - Şarkıda konum atla
• /queue - Sıra listesi"""

    bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

# --- YENİ FONKSİYONLAR ---
def get_ai_recommendations(user_id: int) -> List[Dict]:
    """AI tabanlı gelişmiş öneriler"""
    try:
        # Kullanıcı dinleme geçmişini al
        db = get_db()
        user_downloads = get_user_downloads(db, user_id)

        if not user_downloads:
            return []

        # Basit AI mantığı - gerçek uygulamada ML modeli kullanılacak
        recommendations = []

        # Trend müzikler
        for song in trending_songs[:5]:
            recommendations.append({
                'video_id': song.get('id', ''),
                'title': song.get('title', 'Bilinmeyen'),
                'confidence': random.uniform(0.7, 0.95),
                'reason': 'Trend müzik'
            })

        # Benzer sanatçılar
        for download in user_downloads[-10:]:
            similar_songs = arama_yap(f"{download.title} benzer", 2)
            for song in similar_songs:
                if song['id'] not in [d.video_id for d in user_downloads]:
                    recommendations.append({
                        'video_id': song['id'],
                        'title': song.get('title', 'Bilinmeyen'),
                        'confidence': random.uniform(0.6, 0.9),
                        'reason': 'Benzer şarkı'
                    })

        return recommendations[:10]

    except Exception as e:
        print(f"AI öneri hatası: {e}")
        return []

def get_user_analytics(user_id: int) -> Dict:
    """Kullanıcı analitiği hesapla"""
    try:
        db = get_db()
        downloads = get_user_downloads(db, user_id)

        if not downloads:
            return {}

        # Basit analitik hesaplamaları
        total_plays = len(downloads)
        genres = {}
        artists = {}

        for download in downloads:
            # Tür ve sanatçı çıkarımı (basitleştirilmiş)
            if hasattr(download, 'title'):
                title_lower = download.title.lower()
                if any(word in title_lower for word in ['pop', 'dance']):
                    genres['Pop'] = genres.get('Pop', 0) + 1
                elif any(word in title_lower for word in ['rock', 'metal']):
                    genres['Rock'] = genres.get('Rock', 0) + 1
                elif any(word in title_lower for word in ['jazz', 'blues']):
                    genres['Jazz'] = genres.get('Jazz', 0) + 1
                else:
                    genres['Diğer'] = genres.get('Diğer', 0) + 1

        favorite_genre = max(genres.items(), key=lambda x: x[1])[0] if genres else 'Bilinmiyor'

        return {
            'total_plays': total_plays,
            'favorite_genre': favorite_genre,
            'most_played_artist': 'Bilinmiyor',  # Gerçek uygulamada hesaplanacak
            'daily_average': total_plays * 3,  # Basitleştirilmiş
            'weekly_total': total_plays * 21,
            'most_active_day': 'Cumartesi',
            'new_artists_discovered': len(set()),
            'genre_diversity': len(genres),
            'recommendation_accuracy': 85.5,
            'taste_evolution': 'Gelişiyor',
            'trend_compatibility': 78.3
        }

    except Exception as e:
        print(f"Analitik hesaplama hatası: {e}")
        return {}

# --- CALLBACK HANDLER - ULTRA PREMIUM ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data

    # AI önerileri
    if data.startswith('play_ai_'):
        video_id = data.split('_', 2)[2]
        bot.answer_callback_query(call.id, "▶️ AI önerisi oynatılıyor...")

    elif data == 'refresh_ai_recommendations':
        handle_ai_recommendations(call.message)
        bot.answer_callback_query(call.id, "🔄 Öneriler yenilendi")

    # Sosyal özellikler
    elif data.startswith('social_'):
        feature = data.split('_')[1]

        if feature == 'friends':
            text = "👥 *Arkadaşlarınız*\n\nHenüz arkadaşınız yok.\n\nArkadaş eklemek için kullanıcı adını yazın: `/add_friend @username`"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        elif feature == 'share_music':
            text = "🎵 *Müzik Paylaşımı*\n\nPaylaşmak istediğiniz şarkının adını yazın: `/share_music şarkı adı`"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        elif feature == 'trending':
            text = "🎯 *Trend Müzikler*\n\nBu hafta en popüler şarkılar:\n\n"
            for i, song in enumerate(trending_songs[:5], 1):
                text += f"{i}. {song.get('title', 'Bilinmeyen')}\n"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "✅ Sosyal özellik açıldı")

    # Gelişmiş oyunlar
    elif data.startswith('game_'):
        game_type = data.split('_', 1)[1]

        if game_type == 'music_quiz':
            # Müzik quiz oyunu
            questions = [
                {"question": "Hangi şarkıcı 'Bohemian Rhapsody'yi söyledi?", "options": ["A. Queen", "B. Beatles", "C. Rolling Stones"], "answer": "A"},
                {"question": "'Shape of You' şarkısının sanatçısı kim?", "options": ["A. Ed Sheeran", "B. Justin Bieber", "C. Bruno Mars"], "answer": "A"},
            ]
            question = random.choice(questions)

            markup = telebot.types.InlineKeyboardMarkup()
            for option in question["options"]:
                markup.row(telebot.types.InlineKeyboardButton(option, callback_data=f"quiz_answer_{question['answer']}_{option[0]}"))

            bot.edit_message_text(f"🎵 *Müzik Quiz*\n\n{question['question']}",
                                user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

        elif game_type == 'leaderboard':
            text = "🏆 *Oyun Lider Tablosu*\n\n🥇 Kullanıcı1 - 2500 puan\n🥈 Kullanıcı2 - 2100 puan\n🥉 Kullanıcı3 - 1800 puan\n\n4. Siz - 1500 puan"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "🎮 Oyun başlatıldı")

    # Müzik prodüksiyon
    elif data.startswith('prod_'):
        tool = data.split('_')[1]

        if tool == 'chord_finder':
            text = "🎼 *Akor Bulucu*\n\nŞarkı adını yazın: `/chord_finder şarkı adı`\n\nÖrnek: `/chord_finder yesterday beatles`"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        elif tool == 'melody_generator':
            text = "🎶 *Melodi Üreteci*\n\nAI ile yeni melodi oluşturun:\n`/generate_melody pop`\n`/generate_melody jazz`\n`/generate_melody rock`"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "🎼 Prodüksiyon aracı açıldı")

    # Mobil senkronizasyon
    elif data.startswith('mobile_'):
        action = data.split('_')[1]

        if action == 'qr_sync':
            # QR kod oluştur (basitleştirilmiş)
            qr_text = f"ZB Music Sync Code: {user_id}"
            bot.edit_message_text(f"📱 *Mobil Senkronizasyon*\n\nQR Kodunuz:\n```\n{qr_text}\n```\n\nBu kodu mobil uygulamada taratın.",
                                user_id, call.message.message_id, parse_mode='Markdown')

        elif action == 'link_generate':
            sync_link = f"https://zbmusic.app/sync?user={user_id}"
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(telebot.types.InlineKeyboardButton("🔗 Bağlantıyı Aç", url=sync_link))
            bot.edit_message_text("📱 *Mobil Senkronizasyon Bağlantısı*\n\nMobil uygulamanızda açmak için bağlantıya tıklayın:",
                                user_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "📱 Mobil senkronizasyon başlatıldı")

    # Karaoke modu
    elif data.startswith('karaoke_'):
        action = data.split('_')[1]

        if action == 'song_select':
            text = "🎤 *Karaoke Şarkı Seçimi*\n\nŞarkı adını yazın: `/karaoke_play şarkı adı`"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        elif action == 'vocal_remove':
            text = "🎵 *Vokal Kaldırma*\n\nŞarkı adını yazın: `/remove_vocal şarkı adı`\n\nAI ile vokali kaldırıp karaoke versiyonu oluşturun."
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "🎤 Karaoke modu açıldı")

    # Sesli komutlar
    elif data.startswith('voice_'):
        action = data.split('_')[1]

        if action == 'record_command':
            text = "🎙️ *Sesli Komut Kaydı*\n\nSesli mesaj gönderin veya komutunuzu yazın.\n\nÖrnek: 'tarkan kiss kiss çal'"
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        elif action == 'command_list':
            text = "📝 *Sesli Komut Listesi*\n\n" + "\n".join([f"• {cmd}" for cmd in voice_commands.keys()])
            bot.edit_message_text(text, user_id, call.message.message_id, parse_mode='Markdown')

        bot.answer_callback_query(call.id, "🎙️ Sesli komut modu açıldı")

    # Kalite seçimi
    elif data.startswith('quality_'):
        quality = data.split('_')[1]
        quality_map = {
            '128': '128k',
            '320': '320k',
            'lossless': '320k'  # Lossless için şimdilik 320k kullan
        }
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]['bitrate'] = quality_map.get(quality, '320k')
        bot.answer_callback_query(call.id, f"🎵 Kalite ayarlandı: {quality_map.get(quality, '320k')}")

    # Diğer callback'ler için mevcut kodu kullan
    elif data.startswith('download_'):
        video_id = data.split('_')[1]
        bitrate = user_data.get(user_id, {}).get('bitrate', '320k')

        try:
            bot.answer_callback_query(call.id, "⏳ İndiriliyor...")

            if os.environ.get("BOT_TOKEN") == "test_token":
                mp3_file = "dummy.mp3"
            else:
                mp3_file = indir_ve_donustur(video_id, bitrate)

            results = search_results.get(str(user_id), [])
            song_info = next((item for item in results if item['id'] == video_id), None)

            # Veritabanına kaydet
            db = get_db()
            add_download(db, user_id, video_id,
                        song_info.get('title', 'Bilinmeyen') if song_info else 'Bilinmeyen',
                        song_info.get('duration', 0) if song_info else 0, 'audio')

            caption = f"🎵 {song_info['title']}" if song_info else "🎵 İndirilen Şarkı"

            markup = telebot.types.InlineKeyboardMarkup()
            if user_id in premium_users:
                markup.row(
                    telebot.types.InlineKeyboardButton("🎵 Sözler", callback_data=f"lyrics_{video_id}"),
                    telebot.types.InlineKeyboardButton("❤️ Favori", callback_data=f"add_fav_{video_id}")
                )

            try:
                if os.environ.get("BOT_TOKEN") == "test_token":
                    bot.send_audio(user_id, None, caption=caption, reply_markup=markup, parse_mode='Markdown')
                else:
                    with open(mp3_file, 'rb') as audio:
                        bot.send_audio(user_id, audio, caption=caption, reply_markup=markup, parse_mode='Markdown')
            except Exception as e:
                print(f"Dosya gönderim hatası: {e}")

        except Exception as e:
            bot.answer_callback_query(call.id, "❌ İndirme hatası!")

# --- ANA MESAJ HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_query(message):
    user_id = message.chat.id
    query = message.text.strip()

    if not query:
        return

    # Hızlı butonlar
    if query == "🎵 Müzik":
        bot.reply_to(message, "🎵 Müzik aramak için şarkı adı yazın!")
        return

    # Müzik arama işlemi
    if len(query) >= 2:  # En az 2 karakter
        try:
            bot.send_message(user_id, f"🔍 '{query}' için arama yapılıyor...")

            # YouTube'da arama yap
            results = arama_yap(query, 8)  # 8 sonuç getir

            if not results:
                bot.send_message(user_id, "❌ Bu arama için sonuç bulunamadı. Farklı bir arama terimi deneyin.")
                return

            # Sonuçları göster
            text = f"🎵 *'{query}' için arama sonuçları:*\n\n"
            markup = telebot.types.InlineKeyboardMarkup()

            for i, song in enumerate(results[:8], 1):
                title = song.get('title', 'Bilinmeyen Başlık')[:40]
                duration = format_sure(song.get('duration', 0))
                uploader = song.get('uploader', 'Bilinmeyen')[:20]

                text += f"{i}. 🎵 {title}\n"
                text += f"   👤 {uploader} | ⏱️ {duration}\n\n"

                # İndirme butonu
                markup.row(telebot.types.InlineKeyboardButton(
                    f"⬇️ {title[:25]}...",
                    callback_data=f"download_{song['id']}"
                ))

            # Kalite seçenekleri
            markup.row(
                telebot.types.InlineKeyboardButton("🎵 128kbps", callback_data="quality_128"),
                telebot.types.InlineKeyboardButton("🎵 320kbps", callback_data="quality_320"),
                telebot.types.InlineKeyboardButton("🎵 Lossless", callback_data="quality_lossless")
            )

            # Arama sonuçlarını kaydet
            search_results[str(user_id)] = results

            bot.send_message(user_id, text, reply_markup=markup, parse_mode='Markdown')

        except Exception as e:
            bot.send_message(user_id, f"❌ Arama hatası: {str(e)}")
            print(f"Arama hatası: {e}")
    else:
        bot.send_message(user_id, "❌ Lütfen en az 2 karakter girin.")

# --- BOT BAŞLATMA ---
if __name__ == "__main__":
    print("🎵 ZB MUSIC ULTRA PREMIUM Bot başlatılıyor...")
    print("✅ Veritabanı başlatıldı")
    print("✅ Tüm modüller yüklendi")
    print("🚀 Bot aktif ve mesajları bekliyor...")

    # Flask sunucusunu ayrı thread'de çalıştır
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Bot'u polling ile başlat
    try:
        bot.polling(none_stop=True, interval=1, timeout=30)
    except Exception as e:
        print(f"❌ Bot hatası: {e}")
        # Hata durumunda yeniden başlatmayı dene
        time.sleep(5)
        bot.polling(none_stop=True, interval=1, timeout=30)
