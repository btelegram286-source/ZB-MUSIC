"""
Basitleştirilmiş veritabanı modülü - Python 3.13 uyumlu
"""
import sqlite3
from datetime import datetime
import os

# Veritabanı bağlantısı
DATABASE_PATH = 'zb_music.db'

def get_db():
    """Veritabanı bağlantısı döndürür"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Veritabanını başlatır"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Users tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Downloads tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            title TEXT,
            duration INTEGER,
            download_type TEXT,
            downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Veritabanı başlatıldı")

def get_user(db, telegram_id: int):
    """Kullanıcıyı ID ile getirir"""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone()

def create_user(db, telegram_id: int, username: str = None, first_name: str = None):
    """Yeni kullanıcı oluşturur"""
    cursor = db.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, created_at, last_activity)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ''', (telegram_id, username, first_name))
    db.commit()

    # Kullanıcıyı döndür
    return get_user(db, telegram_id)

def get_user_downloads(db, telegram_id: int, limit: int = 50):
    """Kullanıcının indirme geçmişini getirir"""
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM downloads
        WHERE user_id = ?
        ORDER BY downloaded_at DESC
        LIMIT ?
    ''', (telegram_id, limit))
    return cursor.fetchall()

def add_download(db, telegram_id: int, video_id: str, title: str, duration: int, download_type: str):
    """İndirme kaydı ekler"""
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO downloads (user_id, video_id, title, duration, download_type, downloaded_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (telegram_id, video_id, title, duration, download_type))
    db.commit()
    return True

def get_music_info(db, video_id: str):
    """Müzik bilgilerini getirir (stub)"""
    return None

def update_music_library(db, video_id: str, **kwargs):
    """Müzik kütüphanesini günceller (stub)"""
    pass

def get_user_favorites(db, telegram_id: int):
    """Kullanıcının favorilerini getirir (stub)"""
    return []

def update_user_stats(db, telegram_id: int, **kwargs):
    """Kullanıcı istatistiklerini günceller (stub)"""
    pass

# Veritabanını başlat
init_db()
