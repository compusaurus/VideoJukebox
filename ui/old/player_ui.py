#ui/player_ui.py
# video_jukebox/ui/player_ui.py
import tkinter as tk
import logging
logger = logging.getLogger("VideoJukebox.CreditManager") # Get a child logger
class PlayerUI:
    def __init__(self, player_tk_window, video_player_instance):
        self.window = player_tk_window # This is the Toplevel window passed from main_app
        self.video_player = video_player_instance

        # Ensure the window has a black background, already set in main.py
        # self.window.configure(bg='black')

        # Create a frame within the Toplevel window for VLC to embed into.
        # This frame will fill the entire player window.
        self.video_frame = tk.Frame(self.window, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)

        # Make sure the frame is realized before trying to get its winfo_id
        self.window.update_idletasks()

        if self.video_player:
            self.video_player.embed_into_frame(self.video_frame)
        else:
            # Fallback if no video player (e.g., for testing UI layout)
            fallback_label = tk.Label(self.video_frame, text="Video Playback Area (VLC not connected)",
                                      bg="black", fg="white", font=("Arial", 24))
            fallback_label.pack(expand=True)

        logger.info("PlayerUI initialized and video frame prepared for VLC.")

    def update_for_new_video(self):
        """
        Called when a new video starts. Could be used to display overlays if needed,
        but VLC handles the video directly in the embedded frame.
        """
        logger.info("PlayerUI notified of new video. (No direct action needed for VLC display)")
        pass

    # Add any other methods if the PlayerUI needs to control aspects of playback
    # or display information related to the video. For now, it's mostly a container.