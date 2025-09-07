import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import sqlite3

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from ZB_MUSIC.ZB_MUSIC.database_simple_final import (
    get_db, init_db, get_user, create_user, get_user_downloads,
    add_download, get_music_info, update_music_library,
    get_user_favorites, update_user_stats
)

from ZB_MUSIC.ZB_MUSIC.lyrics_api import (
    LyricsAPI, get_lyrics_command, extract_artist_from_title
)

from ZB_MUSIC.ZB_MUSIC.recommendations import (
    MusicRecommender, get_recommendations_for_user, update_user_recommendations
)

from ZB_MUSIC.ZB_MUSIC.spotify_integration import SpotifyIntegration

class TestDatabaseModule:
    """Test suite for database_simple_final module"""

    def setup_method(self):
        """Setup before each test"""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Patch the database path
        import ZB_MUSIC.ZB_MUSIC.database_simple_final as db_module
        db_module.DATABASE_PATH = self.temp_db.name

        # Initialize the test database
        init_db()

    def teardown_method(self):
        """Cleanup after each test"""
        os.unlink(self.temp_db.name)

    def test_create_and_get_user(self):
        """Test user creation and retrieval"""
        db = sqlite3.connect(self.temp_db.name)
        db.row_factory = sqlite3.Row

        try:
            # Create user
            user = create_user(db, 123456789, "testuser", "Test User")

            assert user is not None
            assert user['telegram_id'] == 123456789
            assert user['username'] == "testuser"
            assert user['first_name'] == "Test User"

            # Get user
            retrieved_user = get_user(db, 123456789)
            assert retrieved_user is not None
            assert retrieved_user['telegram_id'] == 123456789
        finally:
            db.close()

    def test_add_and_get_downloads(self):
        """Test adding and retrieving downloads"""
        db = sqlite3.connect(self.temp_db.name)
        db.row_factory = sqlite3.Row

        try:
            # Create user first
            create_user(db, 123456789)

            # Add download
            result = add_download(db, 123456789, "test123", "Test Song", 180, "audio")
            assert result is True

            # Get downloads
            downloads = get_user_downloads(db, 123456789)
            assert len(downloads) == 1
            assert downloads[0]['video_id'] == "test123"
            assert downloads[0]['title'] == "Test Song"
        finally:
            db.close()

    def test_get_user_favorites_empty(self):
        """Test getting user favorites (should be empty for simple db)"""
        db = next(get_db())

        favorites = get_user_favorites(db, 123456789)
        assert favorites == []

    def test_update_user_stats_stub(self):
        """Test updating user stats (stub function)"""
        db = next(get_db())

        # Should not raise exception
        update_user_stats(db, 123456789, total_downloads=5)

class TestLyricsAPIModule:
    """Test suite for lyrics_api module"""

    def test_clean_song_title(self):
        """Test song title cleaning"""
        api = LyricsAPI()

        # Test various title formats
        assert api.clean_song_title("Song Name (feat. Artist)") == "song name"
        assert api.clean_song_title("Song Name - Remix") == "song name"
        assert api.clean_song_title("Song Name [Official Video]") == "song name [official video]"

    @patch('ZB_MUSIC.ZB_MUSIC.lyrics_api.requests.get')
    def test_search_lyrics_azlyrics(self, mock_get):
        """Test AZLyrics search"""
        api = LyricsAPI()

        # Mock response with the correct AZLyrics format
        mock_response = Mock()
        mock_response.text = """<!-- Usage of azlyrics.com content by any third-party lyrics provider is prohibited by our licensing agreement. Sorry about that. -->[Verse 1] Test lyrics content</div>"""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        lyrics = api.search_lyrics_azlyrics("Test Song", "Test Artist")
        assert lyrics is not None
        assert "Test lyrics content" in lyrics

    def test_format_lyrics(self):
        """Test lyrics formatting"""
        api = LyricsAPI()

        lyrics = "[Verse 1]\nTest lyrics\n[Chorus]\nMore lyrics"
        formatted = api.format_lyrics(lyrics)

        assert "🎵 *Şarkı Sözleri*" in formatted
        assert lyrics in formatted

    def test_extract_artist_from_title(self):
        """Test artist extraction from title"""
        # Test various formats
        artist, title = extract_artist_from_title("Artist - Song Title")
        assert artist == "Artist"
        assert title == "Song Title"

        artist, title = extract_artist_from_title("Song Title by Artist")
        assert artist == "Song Title"  # Song comes first, then "by", then artist
        assert title == "Artist"

        artist, title = extract_artist_from_title("Song Title | Artist")
        assert artist == "Song Title"  # Song comes first, then "|", then artist
        assert title == "Artist"

    @patch('ZB_MUSIC.ZB_MUSIC.lyrics_api.get_db')
    @patch('ZB_MUSIC.ZB_MUSIC.lyrics_api.get_music_info')
    def test_get_lyrics_with_cache(self, mock_get_music_info, mock_get_db):
        """Test lyrics retrieval with caching"""
        api = LyricsAPI()

        # Mock database functions
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_music_info = Mock()
        mock_music_info.lyrics = "Cached lyrics"
        mock_get_music_info.return_value = mock_music_info

        lyrics = api.get_lyrics("test123", "Test Song", "Test Artist")
        assert lyrics == "Cached lyrics"

class TestRecommendationsModule:
    """Test suite for recommendations module"""

    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_db')
    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_user')
    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_user_downloads')
    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_user_favorites')
    def test_music_recommender_init(self, mock_get_favorites, mock_get_downloads, mock_get_user, mock_get_db):
        """Test MusicRecommender initialization"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])  # Return an iterator

        recommender = MusicRecommender()
        assert recommender.db == mock_db

    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_db')
    def test_get_user_listening_history(self, mock_get_db):
        """Test getting user listening history"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        # Mock user and downloads with proper object-like structure
        with patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_user') as mock_get_user, \
             patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_user_downloads') as mock_get_downloads, \
             patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_user_favorites') as mock_get_favorites:

            mock_get_user.return_value = {'id': 1, 'telegram_id': 123456789}

            # Create mock objects for favorites
            mock_fav1 = Mock()
            mock_fav1.video_id = 'vid2'
            mock_fav1.title = 'Song 2'
            mock_fav1.uploader = 'Artist 2'
            mock_get_favorites.return_value = [mock_fav1]

            # Create mock objects for downloads
            mock_dl1 = Mock()
            mock_dl1.video_id = 'vid1'
            mock_dl1.title = 'Song 1'
            mock_dl1.uploader = 'Artist 1'
            mock_get_downloads.return_value = [mock_dl1]

            recommender = MusicRecommender()
            history = recommender.get_user_listening_history(123456789)

            assert len(history) == 2
            assert history[0]['type'] == 'favorite'
            assert history[1]['type'] == 'download'

    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_db')
    def test_extract_genres_and_artists(self, mock_get_db):
        """Test genre and artist extraction"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        recommender = MusicRecommender()

        history = [
            {'uploader': 'Artist 1'},
            {'uploader': 'Artist 2'},
            {'uploader': 'Artist 1'},
        ]

        preferences = recommender.extract_genres_and_artists(history)

        assert 'artists' in preferences
        assert 'genres' in preferences
        assert 'Artist 1' in preferences['artists']

    @patch('ZB_MUSIC.ZB_MUSIC.recommendations.get_db')
    def test_generate_recommendations_insufficient_data(self, mock_get_db):
        """Test recommendations with insufficient data"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        with patch.object(MusicRecommender, 'get_user_listening_history') as mock_history, \
             patch.object(MusicRecommender, 'get_popular_recommendations') as mock_popular:

            mock_history.return_value = [{'uploader': 'Artist'}]  # Less than 5 items
            mock_popular.return_value = [{'video_id': 'pop1', 'title': 'Popular Song'}]

            recommender = MusicRecommender()
            recommendations = recommender.generate_recommendations(123456789)

            mock_popular.assert_called_once()

class TestSpotifyIntegrationModule:
    """Test suite for spotify_integration module"""

    @patch.dict(os.environ, {
        'SPOTIFY_CLIENT_ID': 'test_client_id',
        'SPOTIFY_CLIENT_SECRET': 'test_client_secret'
    })
    def test_spotify_integration_init(self):
        """Test SpotifyIntegration initialization"""
        spotify = SpotifyIntegration()

        assert spotify.client_id == 'test_client_id'
        assert spotify.client_secret == 'test_client_secret'
        assert spotify.sp_oauth is not None

    @patch.dict(os.environ, {}, clear=True)
    def test_spotify_integration_init_no_credentials(self):
        """Test SpotifyIntegration initialization without credentials"""
        spotify = SpotifyIntegration()

        assert spotify.client_id is None
        assert spotify.client_secret is None
        assert spotify.sp_oauth is None

    @patch('ZB_MUSIC.ZB_MUSIC.spotify_integration.spotipy.Spotify')
    def test_get_user_playlists(self, mock_spotify):
        """Test getting user playlists"""
        spotify = SpotifyIntegration()
        spotify.sp = Mock()

        # Mock playlist response
        mock_response = {
            'items': [
                {
                    'id': 'playlist1',
                    'name': 'Test Playlist',
                    'tracks': {'total': 10}
                }
            ],
            'next': None
        }
        spotify.sp.current_user_playlists.return_value = mock_response

        playlists = spotify.get_user_playlists()

        assert len(playlists) == 1
        assert playlists[0]['id'] == 'playlist1'
        assert playlists[0]['name'] == 'Test Playlist'

    @patch('ZB_MUSIC.ZB_MUSIC.spotify_integration.spotipy.Spotify')
    def test_search_track(self, mock_spotify):
        """Test track search"""
        spotify = SpotifyIntegration()
        spotify.sp = Mock()

        # Mock search response
        mock_response = {
            'tracks': {
                'items': [
                    {
                        'id': 'track1',
                        'name': 'Test Track',
                        'artists': [{'name': 'Test Artist'}],
                        'duration_ms': 180000,
                        'external_urls': {'spotify': 'https://spotify.com/track1'}
                    }
                ]
            }
        }
        spotify.sp.search.return_value = mock_response

        tracks = spotify.search_track("test query")

        assert len(tracks) == 1
        assert tracks[0]['name'] == 'Test Track'
        assert tracks[0]['artists'] == ['Test Artist']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
