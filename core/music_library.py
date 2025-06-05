#core/music_library.py
import os
import re # For parsing filenames
import logging

class MusicLibrary:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.videos = []
        # Get a logger instance specifically for this class
        self.logger = logging.getLogger("VideoJukebox.MusicLibrary") # Store as self.logger
        self.logger.info("MusicLibrary initialized.") # Example log
        
    def scan_videos(self):
        self.videos = []
        music_dir = self.settings_manager.get("music_video_directory")
        if not music_dir or not os.path.isdir(music_dir):
            print(f"Music video directory not set or invalid: {music_dir}")
            return

        blocked_artists = [a.lower() for a in self.settings_manager.get("blocked_artists", [])]
        blocked_genres = [g.lower() for g in self.settings_manager.get("blocked_genres", [])]
        blocked_tracks_paths = self.settings_manager.get("blocked_tracks", [])


        supported_formats = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv') # Add more if needed

        for root, _, files in os.walk(music_dir):
            for file in files:
                if file.lower().endswith(supported_formats):
                    full_path = os.path.join(root, file)
                    
                    # Simple parsing: "Artist - Title.ext"
                    # More complex parsing might involve looking for NFO files or embedded metadata
                    filename_no_ext = os.path.splitext(file)[0]
                    parts = re.split(r'\s+-\s+', filename_no_ext, 1)
                    artist = parts[0].strip() if len(parts) > 0 else "Unknown Artist"
                    title = parts[1].strip() if len(parts) > 1 else filename_no_ext.strip()
                    genre = "Unknown" # Placeholder, could come from folder structure or NFO

                    # Apply rules
                    if artist.lower() in blocked_artists:
                        self.logger.debug(f"Skipping blocked artist: {artist}")
                        continue
                    if genre.lower() in blocked_genres: # Requires genre detection
                        self.logger.debug(f"Skipping blocked genre: {genre}")
                        continue
                    if full_path in blocked_tracks_paths:
                        self.logger.debug(f"Skipping blocked track: {full_path}")
                        continue

                    self.videos.append({
                        'artist': artist,
                        'title': title,
                        'path': full_path,
                        'genre': genre, # Add genre if you parse it
                        'cost': self.settings_manager.get("default_credit_cost", 1) # Add default cost
                    })
        print(f"Found {len(self.videos)} videos.")
        self.logger.info(f"Scan complete. Found {len(self.videos)} videos.") # Use self.logger
        # Sort videos, e.g., by artist then title
        self.videos.sort(key=lambda x: (x['artist'].lower(), x['title'].lower()))
        

    def search(self, query):
        query_lower = query.lower().strip() # Ensure it's lower and stripped

        # If query is empty after stripping, return all videos
        if not query_lower: 
            self.logger.debug("Search query is empty, returning all videos.") # Assuming you have self.logger
            return self.get_all_videos() 

        results = [
            video for video in self.videos
            if query_lower in video['artist'].lower() or query_lower in video['title'].lower()
        ]
        self.logger.debug(f"Search for '{query}' found {len(results)} results.")
        return results
        
    def get_all_videos(self):
        return list(self.videos) # Return a copy

    def get_artists(self):
        return sorted(list(set(v['artist'] for v in self.videos)))

    def get_genres(self): # if you implement genre
        return sorted(list(set(v['genre'] for v in self.videos)))