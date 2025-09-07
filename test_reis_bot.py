import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the bot functions
from reis_bot_ultra_premium import (
    arama_yap,
    format_sure,
    get_ai_recommendations,
    get_user_analytics,
    TEMP_DIR,
    user_data,
    search_results,
    trending_songs,
    premium_users
)

class TestReisBot:
    """Comprehensive test suite for Reis Bot Ultra Premium"""

    def setup_method(self):
        """Setup before each test"""
        # Clear global data
        user_data.clear()
        search_results.clear()
        trending_songs.clear()

        # Add some test data
        trending_songs.extend([
            {'id': 'test1', 'title': 'Test Song 1'},
            {'id': 'test2', 'title': 'Test Song 2'},
        ])

    def teardown_method(self):
        """Cleanup after each test"""
        user_data.clear()
        search_results.clear()
        trending_songs.clear()

    @patch('reis_bot_ultra_premium.yt_dlp.YoutubeDL')
    def test_arama_yap_success(self, mock_ydl):
        """Test successful YouTube search"""
        # Mock the YouTubeDL instance
        mock_instance = Mock()
        mock_instance.extract_info.return_value = {
            'entries': [
                {'id': 'video1', 'title': 'Test Video 1', 'duration': 180},
                {'id': 'video2', 'title': 'Test Video 2', 'duration': 240}
            ]
        }
        # Set up context manager
        mock_instance.__enter__ = Mock(return_value=mock_instance)
        mock_instance.__exit__ = Mock(return_value=None)
        mock_ydl.return_value = mock_instance

        results = arama_yap("test query", 2)

        assert len(results) == 2
        assert results[0]['id'] == 'video1'
        assert results[1]['id'] == 'video2'
        mock_ydl.assert_called_once()
        mock_instance.extract_info.assert_called_once_with("ytsearch2:test query", download=False)

    @patch('reis_bot_ultra_premium.yt_dlp.YoutubeDL')
    def test_arama_yap_failure(self, mock_ydl):
        """Test YouTube search failure"""
        mock_instance = Mock()
        mock_instance.extract_info.side_effect = Exception("Network error")
        mock_ydl.return_value = mock_instance

        results = arama_yap("test query")

        assert results == []
        mock_ydl.assert_called_once()

    def test_format_sure(self):
        """Test time formatting function"""
        assert format_sure(65) == "1:05"
        assert format_sure(3661) == "61:01"
        assert format_sure("125") == "2:05"
        assert format_sure("invalid") == "Bilinmiyor"
        assert format_sure(None) == "Bilinmiyor"

    @patch('reis_bot_ultra_premium.get_db')
    @patch('reis_bot_ultra_premium.get_user_downloads')
    def test_get_ai_recommendations_with_downloads(self, mock_get_downloads, mock_get_db):
        """Test AI recommendations with user download history"""
        # Mock database
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Mock user downloads
        mock_downloads = [
            Mock(title="Test Song 1", video_id="vid1"),
            Mock(title="Test Song 2", video_id="vid2")
        ]
        mock_get_downloads.return_value = mock_downloads

        # Mock arama_yap for similar songs
        with patch('reis_bot_ultra_premium.arama_yap') as mock_arama:
            mock_arama.return_value = [
                {'id': 'new1', 'title': 'New Song 1'},
                {'id': 'new2', 'title': 'New Song 2'}
            ]

            recommendations = get_ai_recommendations(123456)

            assert len(recommendations) > 0
            assert 'video_id' in recommendations[0]
            assert 'title' in recommendations[0]
            assert 'confidence' in recommendations[0]
            assert 0.5 <= recommendations[0]['confidence'] <= 1.0

    @patch('reis_bot_ultra_premium.get_db')
    @patch('reis_bot_ultra_premium.get_user_downloads')
    def test_get_ai_recommendations_no_downloads(self, mock_get_downloads, mock_get_db):
        """Test AI recommendations with no download history"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_downloads.return_value = []

        recommendations = get_ai_recommendations(123456)

        assert recommendations == []

    @patch('reis_bot_ultra_premium.get_db')
    @patch('reis_bot_ultra_premium.get_user_downloads')
    def test_get_user_analytics_with_downloads(self, mock_get_downloads, mock_get_db):
        """Test user analytics calculation"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Mock downloads with titles containing genre keywords
        mock_downloads = [
            Mock(title="Pop Song Dance", video_id="vid1"),
            Mock(title="Rock Metal Song", video_id="vid2"),
            Mock(title="Jazz Blues Track", video_id="vid3"),
            Mock(title="Regular Song", video_id="vid4")
        ]
        mock_get_downloads.return_value = mock_downloads

        analytics = get_user_analytics(123456)

        assert 'total_plays' in analytics
        assert 'favorite_genre' in analytics
        assert 'daily_average' in analytics
        assert 'weekly_total' in analytics
        assert analytics['total_plays'] == 4
        assert analytics['genre_diversity'] == 4  # Pop, Rock, Jazz, Other

    @patch('reis_bot_ultra_premium.get_db')
    @patch('reis_bot_ultra_premium.get_user_downloads')
    def test_get_user_analytics_no_downloads(self, mock_get_downloads, mock_get_db):
        """Test user analytics with no downloads"""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_get_downloads.return_value = []

        analytics = get_user_analytics(123456)

        assert analytics == {}

    def test_premium_user_check(self):
        """Test premium user verification"""
        assert 123456789 in premium_users
        assert 1275184751 in premium_users
        assert 999999 not in premium_users



    @patch('reis_bot_ultra_premium.arama_yap')
    @patch('reis_bot_ultra_premium.bot')
    def test_music_search_handler(self, mock_bot, mock_arama):
        """Test music search message handler"""
        from reis_bot_ultra_premium import handle_query

        # Mock search results
        mock_arama.return_value = [
            {'id': 'vid1', 'title': 'Song 1', 'duration': 180, 'uploader': 'Artist 1'},
            {'id': 'vid2', 'title': 'Song 2', 'duration': 240, 'uploader': 'Artist 2'}
        ]

        # Mock message
        mock_message = Mock()
        mock_message.chat.id = 123456789
        mock_message.text = "test song"

        mock_bot.send_message = Mock()

        # Call the handler
        handle_query(mock_message)

        # Verify search was called
        mock_arama.assert_called_once_with("test song", 8)

        # Verify message was sent
        assert mock_bot.send_message.call_count >= 1

    def test_empty_query_handler(self):
        """Test handling of empty query"""
        from reis_bot_ultra_premium import handle_query

        mock_message = Mock()
        mock_message.chat.id = 123456789
        mock_message.text = ""

        # Should not crash
        handle_query(mock_message)

    def test_short_query_handler(self):
        """Test handling of very short query"""
        from reis_bot_ultra_premium import handle_query

        mock_message = Mock()
        mock_message.chat.id = 123456789
        mock_message.text = "a"

        # Should send message about minimum length
        with patch('reis_bot_ultra_premium.bot') as mock_bot:
            handle_query(mock_message)
            mock_bot.send_message.assert_called_with(
                123456789,
                "❌ Lütfen en az 2 karakter girin."
            )

    @patch('reis_bot_ultra_premium.bot')
    def test_button_handlers(self, mock_bot):
        """Test quick button handlers"""
        from reis_bot_ultra_premium import handle_query

        mock_message = Mock()
        mock_message.chat.id = 123456789

        # Test music button
        mock_message.text = "🎵 Müzik"
        handle_query(mock_message)
        mock_bot.reply_to.assert_called_with(
            mock_message,
            "🎵 Müzik aramak için şarkı adı yazın!"
        )

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
