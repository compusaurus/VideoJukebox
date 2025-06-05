import os
import time
import vlc

class VLCQueueManager:
    def __init__(self):
        # 1) Create a libVLC instance
        self.vlc_instance = vlc.Instance()
        # 2) Create a MediaListPlayer (handles a playlist under the hood)
        self.media_list_player = vlc.MediaListPlayer()
        # 3) Create an (initially empty) MediaList
        self.media_list = vlc.MediaList()
        # 4) Tell the player to use that list
        self.media_list_player.set_media_list(self.media_list)
        # 5) Optionally grab the underlying "media player" if you need position/volume controls, etc.
        self.inner_player = self.media_list_player.get_media_player()

    def play(self):
        """
        Start playback of the first item in the queue (if not already playing).
        If already playing, this does nothing.
        """
        # media_list_player.play() will start from the current index.
        # If nothing has played yet, it starts from index 0.
        self.media_list_player.play()

    def stop(self):
        """Stop all playback immediately."""
        self.media_list_player.stop()

    def add_to_queue(self, path_to_video: str):
        """
        Enqueue a new video file. If the player is not running, it will begin playback.
        If it IS playing, the video will be appended to the end of the queue.
        """
        if not os.path.isfile(path_to_video):
            raise FileNotFoundError(f"File not found: {path_to_video}")

        # Create a new Media object for this path
        media = self.vlc_instance.media_new(path_to_video)
        # Append it to our media_list
        self.media_list.add_media(media)

        # If nothing is playing right now, start playback automatically
        state = self.inner_player.get_state()
        # VLC states: NothingSpecial, Opening, Buffering, Playing, Paused, Stopped, etc.
        if state in (vlc.State.NothingSpecial, vlc.State.Stopped, vlc.State.Ended):
            self.play()

    def current_state(self):
        """Return a human-readable string of the player's current state."""
        return str(self.inner_player.get_state())

    def queue_contents(self):
        """
        Return a list of file paths currently in the queue, in order.
        (Note: libVLC does not expose a direct “get file path” on each Media in MediaList,
        so we store the file paths ourselves if you want fully accurate tracking.)
        """
        # If you need to track file paths precisely, you can keep your own list.
        # Below is just a demonstration of how you might inspect the MediaList length.
        count = self.media_list.count()
        return [self.media_list.item_at_index(i).get_mrl() for i in range(count)]


if __name__ == "__main__":
    # Example usage: python vlc_queue.py /path/to/video1.mp4 /path/to/video2.mp4
    
    import sys

    mgr = VLCQueueManager()

    # If the user passed file paths on the command line, enqueue them first
    for video_path in sys.argv[1:]:
        try:
            mgr.add_to_queue(video_path)
            print(f"Enqueued: {video_path}")
        except FileNotFoundError as e:
            print(e)

    print("Starting playback (if not already playing).")
    mgr.play()

    # Now demonstrate adding a new file after a delay
    # (In a real app, you'd hook this up to user input / a GUI callback, etc.)
    try:
        while True:
            time.sleep(5)
            state = mgr.current_state()
            print(f"[{time.strftime('%H:%M:%S')}] VLC state: {state}")
            # For demonstration: when current playlist size drops below 2, append another.
            if mgr.media_list.count() < 2:
                # Replace this path with a video you actually have
                extra = "/path/to/another_video.mp4"
                if os.path.isfile(extra):
                    mgr.add_to_queue(extra)
                    print(f"Auto-enqueued: {extra}")
                else:
                    # If the demo file does not exist, just break
                    break
    except KeyboardInterrupt:
        print("\nStopping playback.")
        mgr.stop()
