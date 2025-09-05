import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Test için BOT_TOKEN'ı geçici olarak set et
original_token = os.environ.get('BOT_TOKEN')
os.environ['BOT_TOKEN'] = 'test_token'  # Test modu için
sys.path.append('.')

import reis_bot

# Test sonrası orijinal token'ı geri yükle
if original_token:
    os.environ['BOT_TOKEN'] = original_token

class TestZBMusicBot(unittest.TestCase):

    def setUp(self):
        self.bot = reis_bot.bot
        self.user_id_premium = 123456789
        self.user_id_non_premium = 987654321
        # Premium users setini güncelle
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
        mock_answer_callback.assert_any_call(call.id, "⏳ Şarkı indiriliyor...")

        # Check that send_audio was called with inline keyboard markup
        call_args = mock_send_audio.call_args
        self.assertIsNotNone(call_args, "send_audio was not called")
        args, kwargs = call_args
        self.assertIn('reply_markup', kwargs)
        buttons = kwargs['reply_markup'].keyboard[0]
        self.assertEqual(buttons[0].text, '▶️ Başlat')
        self.assertEqual(buttons[1].text, '⏭️ Sonraki')
        self.assertEqual(buttons[2].text, '⏹️ Durdur')

    def test_queue_commands(self):
        user_id = self.user_id_premium
        # Kuyruğu boş yap
        reis_bot.user_queues[user_id] = []
        message = MagicMock()
        message.chat.id = user_id
        message.text = "/queue"
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.show_queue(message)
            mock_reply.assert_called_with(message, "🎵 Kuyruğunuz boş.")

        # Kuyruğa şarkı ekle ve göster
        reis_bot.user_queues[user_id] = ['video123', 'video456']
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.show_queue(message)
            args, _ = mock_reply.call_args
            self.assertIn("1. video123", args[1])
            self.assertIn("2. video456", args[1])

    def test_playlist_commands(self):
        user_id = self.user_id_premium
        # Playlist yoksa uyarı
        reis_bot.user_playlists[user_id] = {}
        message = MagicMock()
        message.chat.id = user_id
        message.text = "/playlist"
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.manage_playlist(message)
            mock_reply.assert_called_with(message, "📂 Henüz playlistiniz yok. Yeni playlist oluşturmak için /playlist_create <isim> yazın.")

        # Playlist oluştur ve göster
        reis_bot.user_playlists[user_id] = {'Favoriler': ['video123']}
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.manage_playlist(message)
            args, _ = mock_reply.call_args
            self.assertIn("Favoriler", args[1])

    def test_playlist_create_add_remove(self):
        user_id = self.user_id_premium
        message = MagicMock()
        message.chat.id = user_id

        # Playlist oluştur
        message.text = "/playlist_create Favoriler"
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.create_playlist(message)
            mock_reply.assert_called_with(message, "✅ 'Favoriler' isimli playlist oluşturuldu.")

        # Playlist'e şarkı ekle
        message.text = "/playlist_add Favoriler video123"
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.add_to_playlist(message)
            mock_reply.assert_called_with(message, "✅ 'Favoriler' playlistine şarkı eklendi.")

        # Playlist'ten şarkı çıkar
        message.text = "/playlist_remove Favoriler video123"
        with patch.object(self.bot, 'reply_to') as mock_reply:
            reis_bot.remove_from_playlist(message)
            mock_reply.assert_called_with(message, "✅ 'Favoriler' playlistinden şarkı çıkarıldı.")


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
        call_args = mock_send_audio.call_args
        self.assertIsNotNone(call_args, "send_audio was not called")
        args, kwargs = call_args
        self.assertNotIn('reply_markup', kwargs)

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

    @patch('reis_bot.bot.answer_callback_query')
    def test_stop_callback(self, mock_answer_callback):
        call = MagicMock()
        call.message.chat.id = self.user_id_premium
        call.data = 'stop_video123'
        call.id = 'callback5'

        reis_bot.handle_callback(call)
        mock_answer_callback.assert_called_with(call.id, "⏹️ Oynatma durduruldu (simüle).")

if __name__ == '__main__':
    unittest.main()
