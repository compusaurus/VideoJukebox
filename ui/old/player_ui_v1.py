#ui/player_ui.py
# video_jukebox/ui/player_ui.py
import tkinter as tk
import logging
logger = logging.getLogger("VideoJukebox.CreditManager") # Get a child logger
class PlayerUI:
    def __init__(self, player_tk_window, video_player_instance):
        self.window = player_tk_window
        self.video_player = video_player_instance

        self.video_frame = tk.Frame(self.window, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)

        self.window.update_idletasks() # Ensure frame is realized

        if self.video_player:
            # Use the new method to set the target widget for embedding
            self.video_player.set_embedding_widget(self.video_frame)
            logger.info("PlayerUI: Embedding widget set for VideoPlayer.")
        else:
            # Fallback if no video player (e.g., for testing UI layout)
            fallback_label = tk.Label(self.video_frame, text="Video Playback Area (VLC not connected)",
                                      bg="black", fg="white", font=("Arial", 24))
            fallback_label.pack(expand=True)
            logger.warning("PlayerUI: VideoPlayer instance not available for setting embedding widget.")

        logger.info("PlayerUI initialized.") # Use logger

    def update_for_new_video(self):
        """
        Called when a new video starts. Could be used to display overlays if needed,
        but VLC handles the video directly in the embedded frame.
        """
        logger.info("PlayerUI notified of new video. (No direct action needed for display, VideoPlayer handles embedding)")
        pass

    # Add any other methods if the PlayerUI needs to control aspects of playback
    # or display information related to the video. For now, it's mostly a container.