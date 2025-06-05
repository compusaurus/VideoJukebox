# ui/player_ui.py
import tkinter as tk
import logging

logger = logging.getLogger("VideoJukebox.PlayerUI")

class PlayerUI:
    def __init__(self, player_tk_toplevel_window, video_player_instance):
        self.window = player_tk_toplevel_window # This is the Toplevel window from main.py
        self.video_player = video_player_instance

        # Configure the Toplevel window itself (as done in vlc_queue_test_V3.py for its root)
        # The geometry (size/position) is already set by main.py's setup_displays()

        # Make it borderless for a clean player look (optional, but matches test script style)
        # self.window.overrideredirect(True) # Consider if you want this for the Toplevel

        self.window.configure(bg="black") # Already done in main.py, but good to ensure

        # Set window on top (optional, but good for a dedicated player)
        # self.window.attributes("-topmost", True) # Consider if needed

        # Create a frame within the Toplevel window for VLC to embed into.
        self.video_frame = tk.Frame(self.window, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)

        # CRUCIAL: Force window and frame to be fully created and mapped
        # before getting its HWND/XID for VLC.
        logger.debug("PlayerUI: Forcing window update before getting frame ID...")
        self.window.update_idletasks() # Process geometry and pending idle tasks
        self.window.update()          # Process all other pending events, ensuring window is drawn
        logger.debug("PlayerUI: Window update complete.")

        if self.video_player:
            self.video_player.set_embedding_widget(self.video_frame) # This remains the same logic
            logger.info("PlayerUI: Embedding widget set for VideoPlayer.")
            #frame_handle = self.video_frame.winfo_id()
            #if frame_handle:
            #    logger.info(f"PlayerUI: Obtained video_frame handle: {frame_handle} for embedding.")
                # We will now call a method in VideoPlayer that directly does the embedding
                # using the player object it manages internally.
            #    self.video_player.set_drawable_handle_for_embedding(frame_handle)
            #else:
            #    logger.error("PlayerUI: video_frame.winfo_id() returned 0 or None. Cannot embed.")
        else:
            fallback_label = tk.Label(self.video_frame, text="Video Playback Area (VLC not connected)",
                                      bg="black", fg="white", font=("Arial", 24))
            fallback_label.pack(expand=True)
            logger.warning("PlayerUI: VideoPlayer instance not available for setting embedding handle.")
        
        logger.info("PlayerUI initialized.")

    def update_for_new_video(self): # This method might become less relevant
        logger.info("PlayerUI notified of new video (MediaListPlayer handles display in embedded frame).")
        pass