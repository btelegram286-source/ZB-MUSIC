"""
Şarkı sözleri API modülü
"""
import lyricsgenius
import requests
from typing import Optional, Dict
import re
from ZB_MUSIC.ZB_MUSIC.database_simple_final import get_db, get_music_info, update_music_library

class LyricsAPI:
    def __init__(self):
        self.genius_token = "YOUR_GENIUS_ACCESS_TOKEN"  # Environment variable'dan alınmalı
        self.genius = lyricsgenius.Genius(self.genius_token) if self.genius_token != "YOUR_GENIUS_ACCESS_TOKEN" else None

    def clean_song_title(self, title: str) -> str:
        """Şarkı başlığını temizler (feat., remix gibi ekleri çıkarır)"""
        # Yaygın kalıpları temizle
        patterns = [
            r'\s*\(feat\..*\)',
            r'\s*\[feat\..*\]',
            r'\s*-.*remix.*',
            r'\s*-.*version.*',
            r'\s*\(.*remix.*\)',
            r'\s*\[.*remix.*\]',
            r'\s*\(.*live.*\)',
            r'\s*\[.*live.*\]',
            r'\s*\(.*acoustic.*\)',
            r'\s*\[.*acoustic.*\]'
        ]

        cleaned = title.lower()
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def search_lyrics_genius(self, title: str, artist: str = None) -> Optional[str]:
        """Genius API kullanarak şarkı sözleri arar"""
        if not self.genius:
            return None

        try:
            # Şarkı başlığını temizle
            clean_title = self.clean_song_title(title)

            # Sanatçı bilgisi varsa kullan
            if artist:
                query = f"{clean_title} {artist}"
            else:
                query = clean_title

            # Şarkıyı ara
            song = self.genius.search_song(query)

            if song and song.lyrics:
                return song.lyrics

        except Exception as e:
            print(f"Genius API hatası: {e}")

        return None

    def search_lyrics_azlyrics(self, title: str, artist: str = None) -> Optional[str]:
        """AZLyrics'ten şarkı sözleri arar (fallback)"""
        try:
            # URL formatını oluştur
            if artist:
                # Sanatçı ve şarkı adını URL formatına dönüştür
                artist_clean = re.sub(r'[^\w\s]', '', artist).replace(' ', '').lower()
                title_clean = re.sub(r'[^\w\s]', '', title).replace(' ', '').lower()

                url = f"https://www.azlyrics.com/lyrics/{artist_clean}/{title_clean}.html"
            else:
                return None

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # HTML'den sözleri çıkar
            lyrics_match = re.search(r'<!-- Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement\. Sorry about that\. -->(.*?)</div>', response.text, re.DOTALL)

            if lyrics_match:
                lyrics = lyrics_match.group(1)
                # HTML etiketlerini temizle
                lyrics = re.sub(r'<[^>]+>', '', lyrics)
                # Fazla boşlukları temizle
                lyrics = re.sub(r'\n\s*\n', '\n\n', lyrics.strip())
                return lyrics

        except Exception as e:
            print(f"AZLyrics hatası: {e}")

        return None

    def get_lyrics(self, video_id: str, title: str, artist: str = None) -> Optional[str]:
        """Şarkı sözlerini getirir (önbellek ile)"""
        # Önce veritabanından kontrol et
        db = get_db()
        music_info = get_music_info(db, video_id)

        if music_info and music_info.lyrics:
            return music_info.lyrics

        # Sözleri ara
        lyrics = None

        # Önce Genius API dene
        if self.genius:
            lyrics = self.search_lyrics_genius(title, artist)

        # Genius başarısız olursa AZLyrics dene
        if not lyrics:
            lyrics = self.search_lyrics_azlyrics(title, artist)

        # Sözler bulunduysa veritabanına kaydet
        if lyrics:
            update_music_library(db, video_id, lyrics=lyrics)

        return lyrics

    def format_lyrics(self, lyrics: str, max_length: int = 4000) -> str:
        """Şarkı sözlerini Telegram için formatlar"""
        if not lyrics:
            return "❌ Şarkı sözleri bulunamadı."

        # Çok uzun sözleri kısalt
        if len(lyrics) > max_length:
            lyrics = lyrics[:max_length] + "\n\n... (devamı için tam şarkıyı indirin)"

        # Formatla
        formatted = f"🎵 *Şarkı Sözleri*\n\n{lyrics}"

        return formatted

def get_lyrics_command(video_id: str, title: str, artist: str = None) -> str:
    """Şarkı sözleri komutu için ana fonksiyon"""
    lyrics_api = LyricsAPI()
    lyrics = lyrics_api.get_lyrics(video_id, title, artist)

    if lyrics:
        return lyrics_api.format_lyrics(lyrics)
    else:
        return "❌ Bu şarkının sözleri bulunamadı.\n\n💡 *İpuçları:*\n• Farklı bir arama terimi deneyin\n• Şarkı adını ve sanatçıyı doğru yazdığınızdan emin olun\n• Bazı şarkıların sözleri mevcut olmayabilir"

def extract_artist_from_title(title: str) -> tuple:
    """Şarkı başlığından sanatçı adını çıkarır"""
    # Yaygın formatları dene
    patterns = [
        r'^(.+?)\s*-\s*(.+)$',  # Artist - Song
        r'^(.+?)\s*\|\s*(.+)$',  # Artist | Song
        r'^(.+?)\s*by\s*(.+)$',  # Song by Artist
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    return None, title  # Sanatçı bulunamazsa tümünü şarkı adı olarak al
