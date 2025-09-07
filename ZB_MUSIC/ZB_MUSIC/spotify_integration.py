"""
Spotify entegrasyon modülü
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List, Dict, Optional
import os

class SpotifyIntegration:
    def __init__(self):
        self.client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
        self.scope = 'playlist-read-private playlist-read-collaborative user-library-read'

        if not self.client_id or not self.client_secret:
            print("⚠️ Spotify API credentials are not set. Spotify features will be disabled.")
            self.sp_oauth = None
            return

        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = None
        self.token_info = None

    def get_auth_url(self) -> str:
        """Kullanıcıyı yetkilendirme URL'sine yönlendir"""
        auth_url = self.sp_oauth.get_authorize_url()
        return auth_url

    def get_token(self, code: str) -> bool:
        """Yetkilendirme kodundan token al"""
        self.token_info = self.sp_oauth.get_access_token(code)
        if self.token_info:
            self.sp = spotipy.Spotify(auth=self.token_info['access_token'])
            return True
        return False

    def refresh_token(self) -> bool:
        """Token yenile"""
        if self.token_info and 'refresh_token' in self.token_info:
            self.token_info = self.sp_oauth.refresh_access_token(self.token_info['refresh_token'])
            self.sp = spotipy.Spotify(auth=self.token_info['access_token'])
            return True
        return False

    def get_user_playlists(self) -> List[Dict]:
        """Kullanıcının Spotify playlist'lerini getirir"""
        if not self.sp:
            raise Exception("Spotify client not authenticated.")

        playlists = []
        results = self.sp.current_user_playlists()
        while results:
            for item in results['items']:
                playlists.append({
                    'id': item['id'],
                    'name': item['name'],
                    'tracks_total': item['tracks']['total']
                })
            if results['next']:
                results = self.sp.next(results)
            else:
                results = None
        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Belirli bir playlistin şarkılarını getirir"""
        if not self.sp:
            raise Exception("Spotify client not authenticated.")

        tracks = []
        results = self.sp.playlist_items(playlist_id)
        while results:
            for item in results['items']:
                track = item['track']
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'duration_ms': track['duration_ms'],
                    'external_url': track['external_urls']['spotify']
                })
            if results['next']:
                results = self.sp.next(results)
            else:
                results = None
        return tracks

    def search_track(self, query: str, limit: int = 5) -> List[Dict]:
        """Spotify'da şarkı arar"""
        if not self.sp:
            raise Exception("Spotify client not authenticated.")

        results = self.sp.search(q=query, limit=limit, type='track')
        tracks = []
        for item in results['tracks']['items']:
            tracks.append({
                'id': item['id'],
                'name': item['name'],
                'artists': [artist['name'] for artist in item['artists']],
                'duration_ms': item['duration_ms'],
                'external_url': item['external_urls']['spotify']
            })
        return tracks
