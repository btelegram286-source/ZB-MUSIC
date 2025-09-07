"""
Kişiselleştirilmiş müzik önerileri modülü
"""
from typing import List, Dict, Optional
from ZB_MUSIC.ZB_MUSIC.database_simple_final import get_db, get_user, get_user_downloads, get_user_favorites, update_user_stats
from collections import Counter
import random

class MusicRecommender:
    def __init__(self):
        self.db = next(get_db())

    def get_user_listening_history(self, telegram_id: int) -> List[Dict]:
        """Kullanıcının dinleme geçmişini getirir"""
        user = get_user(self.db, telegram_id)
        if not user:
            return []

        # Favoriler ve indirmeler birleştir
        history = []

        favorites = get_user_favorites(self.db, telegram_id)
        for fav in favorites:
            history.append({
                'video_id': fav.video_id,
                'title': fav.title,
                'uploader': fav.uploader,
                'type': 'favorite'
            })

        downloads = get_user_downloads(self.db, telegram_id, limit=100)
        for dl in downloads:
            history.append({
                'video_id': dl.video_id,
                'title': dl.title,
                'uploader': dl.uploader,
                'type': 'download'
            })

        return history

    def extract_genres_and_artists(self, history: List[Dict]) -> Dict[str, List[str]]:
        """Dinleme geçmişinden tür ve sanatçı çıkarır"""
        artists = []
        genres = []

        for item in history:
            if item.get('uploader'):
                artists.append(item['uploader'])

        # En popüler sanatçıları bul
        artist_counts = Counter(artists)
        top_artists = [artist for artist, count in artist_counts.most_common(5)]

        return {
            'artists': top_artists,
            'genres': genres  # Şimdilik boş, ileride genişletilebilir
        }

    def generate_recommendations(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Kullanıcı için kişiselleştirilmiş öneriler üretir"""
        history = self.get_user_listening_history(telegram_id)

        if len(history) < 5:
            # Yeterli veri yoksa genel öneriler
            return self.get_popular_recommendations(limit)

        # Kullanıcı tercihlerini çıkar
        preferences = self.extract_genres_and_artists(history)

        recommendations = []

        # Favori sanatçıların diğer şarkıları
        for artist in preferences['artists'][:3]:
            artist_songs = self.get_artist_songs(artist, exclude_history=history)
            recommendations.extend(artist_songs[:3])

        # Benzer türdeki şarkılar (gelecekte uygulanabilir)
        # similar_genre_songs = self.get_similar_genre_songs(preferences['genres'], exclude_history=history)
        # recommendations.extend(similar_genre_songs[:3])

        # Popüler şarkılar
        popular_songs = self.get_popular_recommendations(5)
        recommendations.extend(popular_songs)

        # Karıştır ve limite göre kes
        random.shuffle(recommendations)
        return recommendations[:limit]

    def get_artist_songs(self, artist: str, exclude_history: List[Dict] = None, limit: int = 5) -> List[Dict]:
        """Belirli bir sanatıcının şarkılarını getirir"""
        if exclude_history is None:
            exclude_history = []

        exclude_ids = {item['video_id'] for item in exclude_history}

        # Veritabanından sanatıcının şarkılarını ara
        # Bu basit bir uygulama, gerçekte daha sofistike arama yapılabilir
        artist_songs = []

        # Müzik kütüphanesinden sanatçı şarkılarını getir
        from database import MusicLibrary
        songs = self.db.query(MusicLibrary).filter(
            MusicLibrary.uploader.ilike(f'%{artist}%')
        ).limit(limit * 2).all()

        for song in songs:
            if song.video_id not in exclude_ids:
                artist_songs.append({
                    'video_id': song.video_id,
                    'title': song.title,
                    'uploader': song.uploader,
                    'duration': song.duration,
                    'reason': f"🎤 {artist} sanatçısından"
                })

        return artist_songs[:limit]

    def get_popular_recommendations(self, limit: int = 10) -> List[Dict]:
        """Popüler şarkıları getirir"""
        from database import MusicLibrary

        # En çok indirilen şarkıları getir
        popular_songs = self.db.query(MusicLibrary).order_by(
            MusicLibrary.download_count.desc()
        ).limit(limit).all()

        recommendations = []
        for song in popular_songs:
            recommendations.append({
                'video_id': song.video_id,
                'title': song.title,
                'uploader': song.uploader,
                'duration': song.duration,
                'reason': '🔥 Popüler şarkı'
            })

        return recommendations

    def get_daily_recommendations(self, telegram_id: int) -> List[Dict]:
        """Günlük öneriler üretir"""
        # Kullanıcının tercihlerine göre günlük öneriler
        recommendations = self.generate_recommendations(telegram_id, limit=5)

        # Zaman damgası ekle
        import datetime
        today = datetime.date.today().isoformat()

        for rec in recommendations:
            rec['date'] = today
            rec['reason'] = f"📅 Günlük öneri - {rec.get('reason', '')}"

        return recommendations

    def get_trending_songs(self, limit: int = 10) -> List[Dict]:
        """Trend şarkıları getirir"""
        from database import MusicLibrary
        import datetime

        # Son 7 günde en çok indirilen şarkılar
        week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)

        trending = self.db.query(MusicLibrary).filter(
            MusicLibrary.last_downloaded >= week_ago
        ).order_by(MusicLibrary.download_count.desc()).limit(limit).all()

        recommendations = []
        for song in trending:
            recommendations.append({
                'video_id': song.video_id,
                'title': song.title,
                'uploader': song.uploader,
                'duration': song.duration,
                'reason': '📈 Trend şarkı'
            })

        return recommendations

def get_recommendations_for_user(telegram_id: int, rec_type: str = 'personal') -> List[Dict]:
    """Kullanıcı için önerileri getirir"""
    recommender = MusicRecommender()

    if rec_type == 'personal':
        return recommender.generate_recommendations(telegram_id)
    elif rec_type == 'daily':
        return recommender.get_daily_recommendations(telegram_id)
    elif rec_type == 'trending':
        return recommender.get_trending_songs()
    elif rec_type == 'popular':
        return recommender.get_popular_recommendations()
    else:
        return recommender.generate_recommendations(telegram_id)

def update_user_recommendations(telegram_id: int):
    """Kullanıcının önerilerini günceller"""
    db = get_db()
    recommendations = get_recommendations_for_user(telegram_id)

    # Önerileri kullanıcı istatistiklerine kaydet
    update_user_stats(db, telegram_id, recommendations_count=len(recommendations))

    return recommendations
