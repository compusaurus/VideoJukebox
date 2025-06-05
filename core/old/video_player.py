#core/video_player.py
import vlc
import platform # To get OS type for VLC embedding
import logging

logger = logging.getLogger("VideoJukebox.VideoPlayer")

class VideoPlayer:
    def __init__(self, settings_manager, on_end_callback=None):
        self.settings_manager = settings_manager
        self.on_end_callback = on_end_callback
        #self.instance = vlc.Instance("--no-xlib") # --no-xlib for some linux issues if not careful
        self.instance = vlc.Instance("--no-xlib --avcodec-hw=none")
        self.player = self.instance.media_player_new()
        self.current_media_path = None
        self.current_song_info = None # To store { 'artist': '...', 'title': '...' }
        self.instance = vlc.Instance("--no-xlib --avcodec-hw=none")
        # Setup event handling for when media ends
        events = self.player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_media_end)
        # You can attach more events: MediaPlayerPlaying, MediaPlayerPaused, MediaPlayerStopped, etc.

    def _handle_media_end(self, event):
        print(f"VLC Event: MediaEnded for {self.current_media_path}")
        if self.on_end_callback:
            self.on_end_callback(event) # Pass the event object

    def play(self, video_path, song_info=None):
        if self.player: # Release previous player if it exists
            self.player.stop()
            self.player.release()
            self.player = None

        self.player = self.instance.media_player_new() # Create a fresh player
        # Re-attach events
        events = self.player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_media_end)
        
        # Re-embed (You'd need access to the frame_widget here, or do it after play in main app)
        # This complicates things as embed_into_frame needs to be called again.
        # One way is to have the main app call embed after calling play,
        # or pass the frame_widget to play method.

    def embed_into_frame(self, frame_widget):
        """
        Embeds the VLC player into a Tkinter Frame.
        The frame_widget must be a Tkinter Frame or Toplevel window.
        """
        # The method to embed depends on the OS
        if platform.system() == "Linux":
            self.player.set_xwindow(frame_widget.winfo_id())
        elif platform.system() == "Windows":
            self.player.set_hwnd(frame_widget.winfo_id())
        elif platform.system() == "Darwin": # macOS
            # For macOS, you might need to use a NSView object.
            # This can be complex with Tkinter. Often requires using vlc.libvlc_media_player_set_nsobject
            # and casting the frame_widget.winfo_id() appropriately, or using a library
            # that bridges Tkinter and Cocoa views.
            # A common workaround is to let VLC manage its own window, but that's not ideal for embedding.
            # For simplicity, we can try set_hwnd, it might work in some XQuartz scenarios.
             try:
                self.player.set_hwnd(frame_widget.winfo_id())
             except Exception as e:
                print(f"Warning: Could not embed VLC on macOS using set_hwnd: {e}")
                print("VLC might open in a separate window or not display correctly.")
        else:
            print(f"Unsupported platform for VLC embedding: {platform.system()}")


    def stop(self):
        self.player.stop()
        self.current_media_path = None
        self.current_song_info = None

    def pause(self):
        self.player.pause() # Toggles pause

    def set_volume(self, volume): # 0-100
        self.player.audio_set_volume(int(volume))

    def get_volume(self):
        return self.player.audio_get_volume()

    def get_state(self):
        """ Returns the current state of the player (e.g., Playing, Paused, Ended). """
        state = self.player.get_state()
        # vlc.State is an enum: NothingSpecial, Opening, Buffering, Playing, Paused, Stopped, Ended, Error
        return state
    
    def get_current_song_info(self):
        return self.current_song_info

    def release(self):
        if self.player:
            self.player.stop()
            self.player.release()
            self.player = None
        if self.instance:
            self.instance.release()
            self.instance = None