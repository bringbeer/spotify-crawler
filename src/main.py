import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict

# Initialize Spotify client
client_credentials_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def download_album_cover(album_id, album_name, cover_dir):
    """Download album cover and save it with album name."""
    try:
        album = sp.album(album_id)
        cover_url = album['images'][0]['url']
        
        if not os.path.exists(cover_dir):
            os.makedirs(cover_dir)
        
        # Sanitize album name: remove/replace special characters and whitespace
        sanitized_name = "".join(c if c.isalnum() else "_" for c in album_name)
        
        response = requests.get(cover_url)
        file_path = os.path.join(cover_dir, f"{sanitized_name}.jpg")
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        return file_path
    except Exception as e:
        print(f"Error downloading cover for {album_name}: {e}")
        return None

def crawl_playlists(playlist_ids, cover_dir="covers"):
    """Crawl playlists and download album covers."""
    album_index = defaultdict(int)
    songs_data = []
    
    for playlist_id in playlist_ids:
        results = sp.playlist_tracks(playlist_id)
        
        while results:
            for item in results['items']:
                track = item['track']
                if track:
                    album = track['album']
                    album_name = album['name']
                    album_id = album['id']
                    
                    # Add to index
                    album_index[album_name] += 1
                    
                    # Download cover
                    cover_path = download_album_cover(album_id, album_name, cover_dir)
                    
                    # Store song data
                    songs_data.append({
                        'title': track['name'],
                        'album': album_name,
                        'cover': cover_path
                    })
            
            # Get next page
            results = sp.next(results) if results['next'] else None
    
    return songs_data, album_index

if __name__ == "__main__":
    # Example playlist IDs
    playlist_ids = ["3vgCWrOBB1CCYzdNhHqQWh",
                     "1yEIaUIEegfO9Dcdwn8dye",
                     "2bfGty56Un6Ne6KgPDQfNX",
                     "02xwU6uxtIOMOxqtLPx4Az",
                     "5Wq1NpgZ2hwRc2MgMYxePM",
                     "07NRNtwOGbAD45StA2s5ys",
                     "3R4JUuEoF40FQJ1scrt658"]
    
    songs, albums = crawl_playlists(playlist_ids)
    
    # Print album index
    print("Album Index:")
    for album, count in sorted(albums.items()):
        print(f"  {album}: {count} songs")
    
    print(f"\nTotal songs: {len(songs)}")
