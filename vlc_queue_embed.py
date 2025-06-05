# vlc_queue_embed.py
import sys
import os
import time
import tkinter as tk
import vlc

class VLCQueueManager:
    def __init__(self, drawable_handle: int):
        """
        drawable_handle: the native HWND (on Windows) or XID (on Linux) 
                         of the window (or frame) where VLC should draw its video.
        """
        # 1) Create a libVLC instance
        self.vlc_instance = vlc.Instance()

        # 2) Create a MediaListPlayer (it manages a playlist internally)
        self.media_list_player = vlc.MediaListPlayer()

        # 3) Create an initially‐empty MediaList
        self.media_list = vlc.MediaList()

        # 4) Tell the MediaListPlayer to use that MediaList
        self.media_list_player.set_media_list(self.media_list)

        # 5) Grab the underlying MediaPlayer so we can embed the window
        self.inner_player = self.media_list_player.get_media_player()

        # 6) Immediately set its drawable to our supplied window handle
        #    On Windows, you use set_hwnd(HWND). 
        #    On Linux you'd call set_xwindow(XID), on macOS set_nsobject(nsobject).
        #
        #    Here we’re assuming Windows. If you need cross‐platform, check
        #    sys.platform and branch accordingly.
        self.inner_player.set_hwnd(drawable_handle)

    def add_to_queue(self, path_to_video: str):
        if not os.path.isfile(path_to_video):
            raise FileNotFoundError(f"File not found: {path_to_video}")

        media = self.vlc_instance.media_new(path_to_video)
        self.media_list.add_media(media)

        # If nothing is playing (Stopped/Ended), start playback
        state = self.inner_player.get_state()
        if state in (vlc.State.NothingSpecial, vlc.State.Stopped, vlc.State.Ended):
            self.media_list_player.play()

    def play(self):
        """Begin (or resume) playback from the first/next item in the queue."""
        self.media_list_player.play()

    def stop(self):
        """Stop playback right away."""
        self.media_list_player.stop()

    def current_state(self):
        return str(self.inner_player.get_state())

    def queue_contents(self):
        return [self.media_list.item_at_index(i).get_mrl() 
                for i in range(self.media_list.count())]


def main():
    # 1) Build a tkinter window on whichever display you like.
    #    For example, to place it on a second monitor, you might do "+1920+0"
    #    if your primary screen is 1920px wide. Adjust the geometry to taste.
    root = tk.Tk()
    root.title("VLC Embedded Queue")
    root.geometry("800x450+100+100")  
    root.configure(bg="black")

    # 2) Create a Frame that will hold VLC’s video
    video_frame = tk.Frame(root, bg="black")
    video_frame.pack(fill=tk.BOTH, expand=1)

    # 3) Force a window update so that winfo_id() is valid
    root.update_idletasks()
    root.update()

    # 4) Grab the native window handle (HWND on Windows)
    window_id = video_frame.winfo_id()

    # 5) Instantiate our VLCQueueManager with that handle
    mgr = VLCQueueManager(drawable_handle=window_id)

    # 6) If the user passed file paths on the command line, enqueue them now
    for video_path in sys.argv[1:]:
        try:
            mgr.add_to_queue(video_path)
            print(f"Enqueued: {video_path}")
        except FileNotFoundError as e:
            print("Error:", e)

    # 7) Kick off playback (if something was enqueued)
    mgr.play()

    # 8) OPTIONAL: In a real app, you’d probably wire up “Add to Queue” buttons, 
    #    file‐dialogs, etc. Here, we’ll just monitor VLC’s state every few seconds 
    #    and quit if the queue is empty.
    def _poll():
        state = mgr.current_state()
        # If VLC is neither Playing nor Paused nor Opening/Buffering—and the queue is empty—exit.
        if state in (str(vlc.State.Ended), str(vlc.State.Stopped)) and mgr.media_list.count() == 0:
            root.quit()
        else:
            # Re‐run this check in 1 second
            root.after(1000, _poll)

    root.after(1000, _poll)
    root.mainloop()

    # Once the tkinter window closes, stop VLC and exit.
    mgr.stop()
    print("Exiting.")

if __name__ == "__main__":
    main()
