import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
from.emotion_mapper import get_spotify_targets
load_dotenv()
import random

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Initialize client
auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID, 
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(auth_manager=auth_manager)

def get_music_recommendation(language, emotion):
    # 1. Get the mood data (Returns playlist_id or genre string)
    mood = get_spotify_targets(emotion, language)
    lang_lower = language.lower()
    
    final_songs = []
    seen_songs = set()
    ignore_keywords = ["darkie", "trap", "phonk", "death squad", "dracula", "morbius", "playlist", "top hits"]

    # --- NEW CHANGE: HANDLE HARDCODED PLAYLISTS (English, Korean, Japanese) ---
    if mood.get('is_playlist'):
        try:
            # Fetch directly from the Curated Playlist ID
            results = sp.playlist_items(mood['playlist_id'], limit=30)
            items = results.get('items', [])
            
            for item in items:
                track = item.get('track')
                if not track: continue
                
                # Check for duplicates
                clean_name = track['name'].split('(')[0].strip().lower()
                if clean_name not in seen_songs:
                    final_songs.append({
                        "song_name": track['name'],
                        "artist_name": ", ".join([a['name'] for a in track['artists']]),
                        "movie_name": track['album']['name'].split('(')[0].strip(),
                        "preview_url": track.get('preview_url') or "Preview not available",
                        "full_song_url": track['external_urls']['spotify']
                    })
                    seen_songs.add(clean_name)
            
            random.shuffle(final_songs)
            return final_songs[:10]
        except Exception as e:
            print(f"Playlist Error: {e}")
            return []

    # --- EXISTING CHANGE: SEARCH LOGIC (Telugu, Hindi, Punjabi) ---
    else:
        search_query = f"{language} {mood['genre']}"
        market_map = {"telugu": "IN", "hindi": "IN", "tamil": "IN", "punjabi": "IN"}
        target_market = market_map.get(lang_lower, "IN")
        
        # Reduced random_start range (0-10 is safer for specific regional searches)
        random_start = random.randint(0, 10) 

        for page in range(3):
            current_offset = random_start + (page * 10)
            try:
                search_results = sp.search(q=search_query, type='track', limit=10, 
                                          offset=current_offset, market=target_market)
                tracks = search_results.get('tracks', {}).get('items', [])
            except:
                break
                
            if not tracks: break

            for track in tracks:
                t_name = track['name'].lower()
                a_names = ", ".join([a['name'] for a in track['artists']]).lower()

                if any(bad in t_name or bad in a_names for bad in ignore_keywords):
                    continue

                clean_name = track['name'].split('(')[0].strip().lower()
                if clean_name not in seen_songs:
                    final_songs.append({
                        "song_name": track['name'],
                        "artist_name": ", ".join([a['name'] for a in track['artists']]),
                        "movie_name": track['album']['name'].split('(')[0].strip(),
                        "preview_url": track.get('preview_url') or "Preview not available",
                        "full_song_url": track['external_urls']['spotify']
                    })
                    seen_songs.add(clean_name)
            
            if len(final_songs) >= 10: break

        random.shuffle(final_songs)
        return final_songs[:10]
