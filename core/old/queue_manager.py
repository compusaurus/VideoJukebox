#core/queue_manager.py
# video_jukebox/core/queue_manager.py

import collections

class QueueManager:
    def __init__(self, credit_manager, music_library):
        self.credit_manager = credit_manager
        self.music_library = music_library # To get song details like cost if needed
        self.play_queue = collections.deque() # Using deque for efficient appends and pops from left
        print("QueueManager initialized.")

    def add_song(self, song_info):
        """
        Adds a song to the queue if affordable.
        song_info is expected to be a dictionary like {'artist': A, 'title': T, 'path': P, 'cost': C}
        """
        cost = song_info.get('cost', self.credit_manager.settings_manager.get("default_credit_cost"))

        if self.credit_manager.can_afford(cost):
            if self.credit_manager.deduct_credits(cost):
                self.play_queue.append(song_info)
                print(f"Added to queue: {song_info['artist']} - {song_info['title']}. Cost: {cost}")
                return True, "Song added to queue."
            else:
                # This case should ideally not be reached if can_afford is checked first
                return False, "Failed to deduct credits (unexpected)."
        else:
            print(f"Cannot add to queue: Insufficient credits for {song_info['title']}. Need {cost}, have {self.credit_manager.get_balance()}")
            return False, f"Insufficient credits. Need {cost}."

    def get_next_song(self):
        if self.play_queue:
            song = self.play_queue.popleft()
            print(f"Next song from queue: {song['artist']} - {song['title']}")
            return song
        print("Queue is empty.")
        return None

    def remove_song(self, index):
        """ Removes a song from the queue by its index. Credits are NOT refunded automatically. """
        if 0 <= index < len(self.play_queue):
            removed_song = self.play_queue[index]
            del self.play_queue[index]
            print(f"Removed from queue: {removed_song['artist']} - {removed_song['title']}")
            return removed_song
        print(f"Invalid index for removing song: {index}")
        return None

    def get_queue_view(self, limit=5):
        """ Returns a list of strings representing the current queue, up to a limit. """
        return [f"{s['artist']} - {s['title']}" for i, s in enumerate(self.play_queue) if i < limit]

    def get_full_queue(self):
        """ Returns the full queue as a list of song_info dictionaries """
        return list(self.play_queue)

    def is_empty(self):
        return len(self.play_queue) == 0

    def clear_queue(self):
        self.play_queue.clear()
        print("Queue cleared.")

    # Future: Methods to save/load queue for persistence
    # def save_queue(self, filepath): ...
    # def load_queue(self, filepath): ...