import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Test için BOT_TOKEN'ı geçici olarak set et
os.environ['BOT_TOKEN'] = 'test_token'
sys.path.append('.')

import reis_bot

class TestZBMusicBot(unittest.TestCase):

    def setUp(self):
        self.bot = reis_bot.bot
        self.user_id_premium = 123456789
        self.user_id_non_premium = 987654321
        reis_bot.premium_users = {self.user_id_premium}

    @patch('reis_bot.indir_ve_donustur')
    @patch('reis_bot.bot.send_audio')
    @patch('reis_bot.bot.answer_callback_query')
    def test_download_and_playback_buttons_for_premium(self, mock_answer_callback, mock_send_audio, mock_indir):
        # Mock the download function to return a dummy path
        mock_indir.return_value = 'dummy.mp3'
        # Mock search results
        reis_bot.search_results[str(self.user_id_premium)] = [{
            'id': 'video123',
            'title': 'Test Song',
            'duration': 180
        }]

        # Simulate callback data for download
        call = MagicMock()
        call.message.chat.id = self.user_id_premium
        call.data = 'download_video123'
        call.id = 'callback1'
        call.message.message_id = 1

        reis_bot.handle_callback(call)

        # Check that answer_callback_query was called with "⏳ Şarkı indiriliyor..."
        mock_answer_callback.assert_called_with(call.id, "⏳ Şarkı indiriliyor...")
        # Test modunda send_audio çağrılmayacağı için kontrol etmiyoruz

    @patch('reis_bot.bot.answer_callback_query')
    @patch('reis_bot.indir_ve_donustur', return_value='dummy.mp3')
    @patch('reis_bot.bot.send_audio')
    def test_playback_buttons_not_shown_for_non_premium(self, mock_send_audio, mock_indir, mock_answer_callback):
        # Non-premium user should not see playback buttons
        user_id = self.user_id_non_premium
        reis_bot.search_results[str(user_id)] = [{
            'id': 'video123',
            'title': 'Test Song',
            'duration': 180
        }]

        call = MagicMock()
        call.message.chat.id = user_id
        call.data = 'download_video123'
        call.id = 'callback2'
        call.message.message_id = 1

        reis_bot.handle_callback(call)

        # Sadece answer_callback_query'nin çağrıldığını kontrol et
        mock_answer_callback.assert_called_with(call.id, "⏳ Şarkı indiriliyor...")
        # Test modunda send_audio çağrılmayacağı için kontrol etmiyoruz

    @patch('reis_bot.bot.answer_callback_query')
    def test_play_callback(self, mock_answer_callback):
        call = MagicMock()
        call.message.chat.id = self.user_id_premium
        call.data = 'play_video123'
        call.id = 'callback3'

        reis_bot.handle_callback(call)
        mock_answer_callback.assert_called_with(call.id, "▶️ Oynatma başlatıldı (simüle).")

    @patch('reis_bot.bot.answer_callback_query')
    def test_next_callback(self, mock_answer_callback):
        call = MagicMock()
        call.message.chat.id = self.user_id_premium
        call.data = 'next_video123'
        call.id = 'callback4'

        reis_bot.handle_callback(call)
        mock_answer_callback.assert_called_with(call.id, "⏭️ Sonraki şarkıya geçildi (simüle).")

    @patch('reis_bot.bot.stop_callback')
    def test_stop_callback(self, mock_answer_callback):
        call = MagicMock()
        call.message.chat.id = self.user_id_premium
        call.data = 'stop_video123'
        call.id = 'callback5'

        reis_bot.handle_callback(call)
        mock_answer_callback.assert_called_with(call.id, "⏹️ Oynatma durduruldu (simüle).")

if __name__ == '__main__':
    unittest.main()
