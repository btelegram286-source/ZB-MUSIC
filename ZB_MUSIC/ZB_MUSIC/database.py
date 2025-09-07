"""
Veritabanı modülü - Kalıcı veri saklama için
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language = Column(String(10), default='tr')
    theme = Column(String(20), default='default')
    avatar_url = Column(String(500))
    is_premium = Column(Boolean, default=False)
    premium_expiry = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    playlists = relationship("Playlist", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")
    downloads = relationship("Download", back_populates="user")
    stats = relationship("UserStats", back_populates="user", uselist=False)

class Playlist(Base):
    __tablename__ = 'playlists'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="playlists")
    songs = relationship("PlaylistSong", back_populates="playlist")

class PlaylistSong(Base):
    __tablename__ = 'playlist_songs'

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id'), nullable=False)
    video_id = Column(String(20), nullable=False)
    title = Column(String(200))
    duration = Column(Integer)
    added_at = Column(DateTime, default=datetime.utcnow)

    playlist = relationship("Playlist", back_populates="songs")

class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    video_id = Column(String(20), nullable=False)
    title = Column(String(200))
    duration = Column(Integer)
    uploader = Column(String(100))
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")

class Download(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    video_id = Column(String(20), nullable=False)
    title = Column(String(200))
    duration = Column(Integer)
    file_size = Column(Integer)
    download_type = Column(String(10))  # 'audio' or 'video'
    downloaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="downloads")

class UserStats(Base):
    __tablename__ = 'user_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    total_downloads = Column(Integer, default=0)
    total_songs = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    playlist_count = Column(Integer, default=0)
    listening_time = Column(Integer, default=0)  # saniye cinsinden
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="stats")

class MusicLibrary(Base):
    __tablename__ = 'music_library'

    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), unique=True, nullable=False)
    title = Column(String(200))
    duration = Column(Integer)
    uploader = Column(String(100))
    view_count = Column(Integer)
    upload_date = Column(String(20))
    download_count = Column(Integer, default=0)
    last_downloaded = Column(DateTime)
    lyrics = Column(Text)
    genre = Column(String(50))

# Veritabanı bağlantısı
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///zb_music.db')
engine = create_engine(DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Veritabanı oturumu döndürür"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Veritabanını başlatır"""
    Base.metadata.create_all(bind=engine)
    print("✅ Veritabanı başlatıldı")

def get_user(db, telegram_id: int):
    """Kullanıcıyı ID ile getirir"""
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def create_user(db, telegram_id: int, username: str = None, first_name: str = None):
    """Yeni kullanıcı oluşturur"""
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_activity(db, telegram_id: int):
    """Kullanıcı aktivitesini günceller"""
    user = get_user(db, telegram_id)
    if user:
        user.last_activity = datetime.utcnow()
        db.commit()

def get_user_playlists(db, telegram_id: int):
    """Kullanıcının playlist'lerini getirir"""
    user = get_user(db, telegram_id)
    if user:
        return user.playlists
    return []

def create_playlist(db, telegram_id: int, name: str, description: str = None):
    """Yeni playlist oluşturur"""
    user = get_user(db, telegram_id)
    if not user:
        return None

    playlist = Playlist(
        user_id=user.id,
        name=name,
        description=description
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist

def add_song_to_playlist(db, telegram_id: int, playlist_name: str, video_id: str, title: str, duration: int):
    """Playlist'e şarkı ekler"""
    user = get_user(db, telegram_id)
    if not user:
        return False

    playlist = db.query(Playlist).filter(
        Playlist.user_id == user.id,
        Playlist.name == playlist_name
    ).first()

    if not playlist:
        return False

    # Şarkının zaten playlist'te olup olmadığını kontrol et
    existing = db.query(PlaylistSong).filter(
        PlaylistSong.playlist_id == playlist.id,
        PlaylistSong.video_id == video_id
    ).first()

    if existing:
        return False

    song = PlaylistSong(
        playlist_id=playlist.id,
        video_id=video_id,
        title=title,
        duration=duration
    )
    db.add(song)
    db.commit()
    return True

def get_user_favorites(db, telegram_id: int):
    """Kullanıcının favorilerini getirir"""
    user = get_user(db, telegram_id)
    if user:
        return user.favorites
    return []

def add_to_favorites(db, telegram_id: int, video_id: str, title: str, duration: int, uploader: str):
    """Favorilere şarkı ekler"""
    user = get_user(db, telegram_id)
    if not user:
        return False

    # Zaten favorilerde mi kontrol et
    existing = db.query(Favorite).filter(
        Favorite.user_id == user.id,
        Favorite.video_id == video_id
    ).first()

    if existing:
        return False

    favorite = Favorite(
        user_id=user.id,
        video_id=video_id,
        title=title,
        duration=duration,
        uploader=uploader
    )
    db.add(favorite)
    db.commit()
    return True

def get_user_downloads(db, telegram_id: int, limit: int = 50):
    """Kullanıcının indirme geçmişini getirir"""
    user = get_user(db, telegram_id)
    if user:
        return db.query(Download).filter(Download.user_id == user.id).order_by(Download.downloaded_at.desc()).limit(limit).all()
    return []

def add_download(db, telegram_id: int, video_id: str, title: str, duration: int, download_type: str):
    """İndirme kaydı ekler"""
    user = get_user(db, telegram_id)
    if not user:
        return False

    download = Download(
        user_id=user.id,
        video_id=video_id,
        title=title,
        duration=duration,
        download_type=download_type
    )
    db.add(download)
    db.commit()
    return True

def update_user_stats(db, telegram_id: int, **kwargs):
    """Kullanıcı istatistiklerini günceller"""
    user = get_user(db, telegram_id)
    if not user:
        return False

    if not user.stats:
        user.stats = UserStats(user_id=user.id)

    for key, value in kwargs.items():
        if hasattr(user.stats, key):
            setattr(user.stats, key, value)

    user.stats.last_updated = datetime.utcnow()
    db.commit()
    return True

def get_music_info(db, video_id: str):
    """Müzik kütüphanesinden şarkı bilgilerini getirir"""
    return db.query(MusicLibrary).filter(MusicLibrary.video_id == video_id).first()

def update_music_library(db, video_id: str, **kwargs):
    """Müzik kütüphanesini günceller"""
    music = get_music_info(db, video_id)
    if not music:
        music = MusicLibrary(video_id=video_id)
        db.add(music)

    for key, value in kwargs.items():
        if hasattr(music, key):
            setattr(music, key, value)

    db.commit()
    return music
