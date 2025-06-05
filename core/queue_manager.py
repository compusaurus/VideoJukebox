# core/queue_manager.py
import collections
import logging

logger = logging.getLogger("VideoJukebox.QueueManager")

class QueueManager:
    def __init__(self, credit_manager, music_library): # video_player is no longer passed directly here for queueing
        self.credit_manager = credit_manager
        self.music_library = music_library
        # Keep a simple Python list of all queued song_info dicts (in playback order)
        self._queued_songs = []
        # This deque can now track song_info objects for UI purposes,
        # while VLC's MediaList handles the actual playback order.
        # Or, we simplify and let the main app manage the mapping if needed.
        # For now, let's keep it simple: it manages credits and tells VideoPlayer what to add.
        self.app_queue_view = collections.deque() # For UI display mainly
        logger.info("QueueManager initialized (MediaListPlayer approach).")

    def add_song_to_system(self, song_info, video_player_instance): # video_player_instance is the argument
        cost = song_info.get('cost', self.credit_manager.settings_manager.get("default_credit_cost"))

        if self.credit_manager.can_afford(cost):
            if not self.credit_manager.deduct_credits(cost):
                logger.warning(f"Credit deduction failed for {song_info['title']} (unexpected).")
                return False, "Credit deduction failed."

            # Use the 'video_player_instance' argument here
            if video_player_instance.add_to_playlist(song_info['path'], song_info):
                self.app_queue_view.append(song_info) 
                logger.info(f"Added to app queue view & VLC playlist: {song_info['artist']} - {song_info['title']}")
                return True, "Song added to queue."
            else:
                logger.error(f"Failed to add {song_info['title']} to VLC playlist. Refunding {cost} credits.")
                self.credit_manager.add_credits(cost) 
                return False, "Failed to add song to playback system."
        else:
            logger.info(f"Cannot add: Insufficient credits for {song_info['title']}.")
            return False, f"Insufficient credits. Need {cost}."

    def get_next_song_for_ui_update(self): # When VLC plays next, app needs to update its UI
        if self.app_queue_view:
            return self.app_queue_view.popleft()
        return None

    def remove_song_from_app_view(self, song_info_to_remove):
        if not song_info_to_remove or 'path' not in song_info_to_remove:
            logger.warning("remove_song_from_app_view: Invalid song_info_to_remove.")
            return False
        
        # Remove based on a unique identifier, like path
        original_len = len(self.app_queue_view)
        self.app_queue_view = collections.deque(
            s for s in self.app_queue_view if s['path'] != song_info_to_remove['path']
        )
        if len(self.app_queue_view) < original_len:
            logger.info(f"Removed '{song_info_to_remove['title']}' from app_queue_view.")
            return True
        else:
            logger.warning(f"Could not find/remove '{song_info_to_remove['title']}' from app_queue_view (path mismatch?).")
            return False

    def get_full_queue(self):
        """
        Return a shallow copy of the list of queued songs (each element is the song_info dict
        you originally passed to add_song_to_system). This is what the management dialog will read.
        """
        return list(self._queued_songs)

    def get_app_queue_view_strings(self, limit=5):
        return [f"{s['artist']} - {s['title']}" for i, s in enumerate(self.app_queue_view) if i < limit]

    def get_full_app_queue(self):
        return list(self.app_queue_view)

    def is_app_queue_empty(self):
        return len(self.app_queue_view) == 0
    
    def clear_app_queue_view(self): # If admin clears
        self.app_queue_view.clear()
        # Also need to tell VideoPlayer to clear its MediaList
        logger.info("App queue view cleared.")