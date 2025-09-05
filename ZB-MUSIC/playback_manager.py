"""
Playback Yönetim Modülü
Müzik botu için gelişmiş playback kontrol sistemi
"""
import time
import random
from typing import Dict, List, Optional
from datetime import datetime

class PlaybackManager:
    def __init__(self):
        self.now_playing: Dict[int, Dict] = {}
        self.playback_state: Dict[int, str] = {}
        self.playback_position: Dict[int, float] = {}
        self.playback_start_time: Dict[int, float] = {}
        self.current_queue_index: Dict[int, int] = {}
        self.user_queues: Dict[int, List[str]] = {}
        self.repeat_mode: Dict[int, str] = {}
        self.shuffle_mode: Dict[int, bool] = {}
        self.music_library: Dict[str, Dict] = {}

    def start_playback(self, user_id: int, video_id: str, queue: List[str] = None):
        """Playback başlat"""
        if queue:
            self.user_queues[user_id] = queue.copy()
            # Mevcut şarkının indeksini bul
            try:
                self.current_queue_index[user_id] = queue.index(video_id)
            except ValueError:
                self.current_queue_index[user_id] = 0

        self.now_playing[user_id] = {
            'video_id': video_id,
            'title': self.music_library.get(video_id, {}).get('title', 'Bilinmeyen'),
            'start_time': time.time(),
            'position': 0
        }
        self.playback_start_time[user_id] = time.time()
        self.playback_position[user_id] = 0
        self.playback_state[user_id] = 'playing'

    def pause_playback(self, user_id: int):
        """Playback duraklat"""
        if self.playback_state.get(user_id) == 'playing':
            # Pozisyonu güncelle
            current_time = time.time()
            start_time = self.playback_start_time.get(user_id, current_time)
            elapsed = current_time - start_time
            self.playback_position[user_id] = elapsed
            self.playback_state[user_id] = 'paused'

    def resume_playback(self, user_id: int):
        """Playback devam ettir"""
        if self.playback_state.get(user_id) == 'paused':
            # Başlangıç zamanını güncelle
            current_pos = self.playback_position.get(user_id, 0)
            self.playback_start_time[user_id] = time.time() - current_pos
            self.playback_state[user_id] = 'playing'

    def stop_playback(self, user_id: int):
        """Playback durdur"""
        self.playback_state[user_id] = 'stopped'
        self.now_playing[user_id] = {}
        self.playback_position[user_id] = 0

    def next_track(self, user_id: int):
        """Sonraki şarkıya geç"""
        queue = self.user_queues.get(user_id, [])
        if not queue:
            self.stop_playback(user_id)
            return None

        current_index = self.current_queue_index.get(user_id, 0)
        repeat_mode_val = self.repeat_mode.get(user_id, 'off')
        shuffle_mode_val = self.shuffle_mode.get(user_id, False)

        if shuffle_mode_val:
            next_index = random.randint(0, len(queue) - 1)
        else:
            if repeat_mode_val == 'one':
                next_index = current_index
            else:
                next_index = (current_index + 1) % len(queue)

        if next_index >= len(queue):
            if repeat_mode_val == 'all':
                next_index = 0
            else:
                self.stop_playback(user_id)
                return None

        self.current_queue_index[user_id] = next_index
        next_video_id = queue[next_index]
        self.start_playback(user_id, next_video_id, queue)
        return next_video_id

    def previous_track(self, user_id: int):
        """Önceki şarkıya geç"""
        queue = self.user_queues.get(user_id, [])
        if not queue:
            return None

        current_index = self.current_queue_index.get(user_id, 0)
        current_pos = self.playback_position.get(user_id, 0)

        # Eğer şarkının başından 3 saniye geçtiyse, aynı şarkıyı başa sar
        if current_pos > 3:
            self.seek_position(user_id, 0)
            return self.now_playing[user_id].get('video_id')

        # Önceki şarkıya geç
        previous_index = (current_index - 1) % len(queue)
        self.current_queue_index[user_id] = previous_index
        prev_video_id = queue[previous_index]
        self.start_playback(user_id, prev_video_id, queue)
        return prev_video_id

    def seek_position(self, user_id: int, position: float):
        """Belirli pozisyona sar"""
        if user_id not in self.now_playing or not self.now_playing[user_id]:
            return False

        video_id = self.now_playing[user_id].get('video_id')
        if video_id and video_id in self.music_library:
            duration = self.music_library[video_id].get('duration', 0)
            if position < 0:
                position = 0
            elif position > duration:
                position = duration

            self.playback_position[user_id] = position
            self.playback_start_time[user_id] = time.time() - position
            return True
        return False

    def update_position(self, user_id: int):
        """Pozisyonu güncelle ve otomatik geçiş kontrolü"""
        if user_id not in self.now_playing or not self.now_playing[user_id]:
            return

        if self.playback_state.get(user_id) != 'playing':
            return

        current_time = time.time()
        start_time = self.playback_start_time.get(user_id, current_time)
        elapsed = current_time - start_time

        # Şarkı süresini kontrol et
        video_id = self.now_playing[user_id].get('video_id')
        if video_id and video_id in self.music_library:
            duration = self.music_library[video_id].get('duration', 0)
            if duration > 0 and elapsed >= duration:
                # Şarkı bitti, sonraki şarkıya geç
                self.next_track(user_id)
                return

        self.playback_position[user_id] = elapsed

    def get_current_status(self, user_id: int) -> Dict:
        """Mevcut playback durumunu döndür"""
        return {
            'now_playing': self.now_playing.get(user_id, {}),
            'state': self.playback_state.get(user_id, 'stopped'),
            'position': self.playback_position.get(user_id, 0),
            'queue_index': self.current_queue_index.get(user_id, 0),
            'repeat_mode': self.repeat_mode.get(user_id, 'off'),
            'shuffle_mode': self.shuffle_mode.get(user_id, False)
        }

    def set_repeat_mode(self, user_id: int, mode: str):
        """Tekrar modunu ayarla"""
        if mode in ['off', 'one', 'all']:
            self.repeat_mode[user_id] = mode

    def set_shuffle_mode(self, user_id: int, enabled: bool):
        """Karıştır modu ayarla"""
        self.shuffle_mode[user_id] = enabled

    def add_to_queue(self, user_id: int, video_id: str):
        """Kuyruğa şarkı ekle"""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = []
        self.user_queues[user_id].append(video_id)

    def remove_from_queue(self, user_id: int, index: int):
        """Kuyruktan şarkı çıkar"""
        if user_id in self.user_queues and 0 <= index < len(self.user_queues[user_id]):
            removed = self.user_queues[user_id].pop(index)
            # İndeksi güncelle
            current_index = self.current_queue_index.get(user_id, 0)
            if index < current_index:
                self.current_queue_index[user_id] = current_index - 1
            elif index == current_index:
                # Çalan şarkı çıkarıldı, sonraki şarkıya geç
                self.next_track(user_id)
            return removed
        return None

# Global instance
playback_manager = PlaybackManager()
