# vlc_interactive_queue_final.py

import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# 0) BEFORE any 'import vlc', force VLC’s own folders onto PATH and VLC_PLUGIN_PATH.
#
#    Make sure these two paths exactly match your installation:
#      vlc_base    = r"C:\Program Files\VideoLAN\VLC"
#      vlc_plugins = os.path.join(vlc_base, "plugins")
# ─────────────────────────────────────────────────────────────────────────────

vlc_base    = r"C:\Program Files\VideoLAN\VLC"
vlc_plugins = os.path.join(vlc_base, "plugins")

# 0A) Add VLC’s root to the OS PATH so Windows can find libvlc.dll:
os.environ["PATH"] = vlc_base + ";" + os.environ.get("PATH", "")

# 0B) Tell libVLC exactly where its "plugins" folder is:
os.environ["VLC_PLUGIN_PATH"] = vlc_plugins

# (At this point, PATH and VLC_PLUGIN_PATH are set for this process.)
# ─────────────────────────────────────────────────────────────────────────────

import ctypes
import ctypes.wintypes
import vlc   # ← Now we import python-vlc, after the environment is correct
import tkinter as tk
from tkinter import filedialog

# ─────────────────────────────────────────────────────────────────────────────
# A helper that enumerates all monitors on Windows so we can place our window
# on the second display (if you have two). Otherwise it uses the primary.
# ─────────────────────────────────────────────────────────────────────────────
def get_monitor_rects():
    user32 = ctypes.windll.user32

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.wintypes.HMONITOR,
        ctypes.wintypes.HDC,
        ctypes.POINTER(ctypes.wintypes.RECT),
        ctypes.c_double
    )

    rects = []
    def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        r = lprcMonitor.contents
        rects.append((r.left, r.top, r.right, r.bottom))
        return 1  # continue enumeration

    user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_callback), 0)
    return rects


class VLCInteractiveQueue:
    def __init__(self):
        # ─────────────────────────────────────────────────────────────────────
        # 1) Determine the rectangle of the second monitor (if available).
        # ─────────────────────────────────────────────────────────────────────
        monitors = get_monitor_rects()
        if len(monitors) >= 2:
            left, top, right, bottom = monitors[1]
        else:
            left, top, right, bottom = monitors[0]

        self.screen_width  = right - left
        self.screen_height = bottom - top
        self.screen_left   = left
        self.screen_top    = top

        # ─────────────────────────────────────────────────────────────────────
        # 2) Create a borderless “cover‐the‐monitor” Tk window on that screen
        # ─────────────────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("VLC Jukebox (Interactive Queue)")
        self.root.overrideredirect(True)  # remove title bar & borders
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_left}+{self.screen_top}")
        self.root.attributes("-topmost", True)

        # 3) Create a frame to host VLC’s video inside that window
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        self.root.update_idletasks()
        self.root.update()
        self.video_window_id = self.video_frame.winfo_id()

        # ─────────────────────────────────────────────────────────────────────
        # 4) Instantiate VLC, then create a MediaList + MediaListPlayer
        # ─────────────────────────────────────────────────────────────────────
        self.instance   = vlc.Instance()
        self.media_list = self.instance.media_list_new()
        if not self.media_list:
            print("ERROR: media_list_new() returned None.")
            print("  → That means libVLC could not load the 'playlist' plugin.")
            print("  → Double‐check that PATH and VLC_PLUGIN_PATH point to the correct folders.")
            self.root.destroy()
            sys.exit(1)

        self.ml_player = self.instance.media_list_player_new()
        if not self.ml_player:
            print("ERROR: media_list_player_new() returned None.")
            self.root.destroy()
            sys.exit(1)

        # Tell the player to use exactly this MediaList:
        self.ml_player.set_media_list(self.media_list)

        # Grab the underlying MediaPlayer to embed its video into our frame
        self.media_player = self.ml_player.get_media_player()
        if not self.media_player:
            print("ERROR: get_media_player() returned None.")
            self.root.destroy()
            sys.exit(1)

        # Embed VLC video into the Tk window’s frame:
        self.media_player.set_hwnd(self.video_window_id)

        # ─────────────────────────────────────────────────────────────────────
        # 5) Draw an “instructions” overlay in the top‐left corner
        # ─────────────────────────────────────────────────────────────────────
        self.instr_label = tk.Label(
            self.root,
            text="Esc: Exit   |   A: Add Videos",
            bg="black",
            fg="white",
            font=("Segoe UI", 12)
        )
        self.instr_label.place(x=10, y=10)

        # ─────────────────────────────────────────────────────────────────────
        # 6) Bind keys:  
        #      - <Escape> quits, 
        #      - “A” (or “a”) pops up a file dialog to enqueue more.
        # ─────────────────────────────────────────────────────────────────────
        self.root.bind("<Escape>", self._exit_on_escape)
        self.root.bind("<a>", self._on_add)
        self.root.bind("<A>", self._on_add)

        # ─────────────────────────────────────────────────────────────────────
        # 7) Start polling VLC’s state and enter the Tk main loop.
        # ─────────────────────────────────────────────────────────────────────
        self._poll_playback()
        self.root.mainloop()
        self.ml_player.stop()

    def _on_add(self, event=None):
        """
        Pressing 'A' brings up a file dialog.  
        Each chosen video gets appended to the existing MediaList.  
        If VLC is currently idle, we immediately call play() to resume.
        """
        # Let the window get its decorations back so the dialog shows properly
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", False)

        paths = filedialog.askopenfilenames(
            title="Select video files to enqueue",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("All Files", "*.*")]
        )

        # Return to borderless, full‐monitor mode
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        if not paths:
            return

        enqueued = False
        for p in paths:
            if os.path.isfile(p):
                m = self.instance.media_new(p)
                self.media_list.add_media(m)
                print(f"✅ Enqueued: {p}")
                enqueued = True
            else:
                print(f"⚠️  Skipped (not found): {p}")

        # If VLC is not already playing, resume playback
        state = self.ml_player.get_state()
        if enqueued and state not in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
            print("▶️  Starting playback…")
            self.ml_player.play()

    def _poll_playback(self):
        """
        Every 500 ms, check if VLC has gone Idle (Ended/Stopped) while there
        are still items left in the MediaList. If so, automatically call play().
        Otherwise do nothing and wait for the user to press “A” again.
        """
        state = self.ml_player.get_state()
        count = self.media_list.count()
        if state in (vlc.State.Ended, vlc.State.Stopped) and count > 0:
            print("▶️  Resuming playback…")
            self.ml_player.play()
        self.root.after(500, self._poll_playback)

    def _exit_on_escape(self, event=None):
        """
        Stop VLC and quit the Tk window when the user presses Escape.
        """
        self.ml_player.stop()
        self.root.quit()


if __name__ == "__main__":
    # You can optionally pass some files on the command line to enqueue immediately:
    initial_paths = sys.argv[1:]
    player = VLCInteractiveQueue()

    if initial_paths:
        for p in initial_paths:
            if os.path.isfile(p):
                m = player.instance.media_new(p)
                player.media_list.add_media(m)
                print(f"✅ Enqueued on start: {p}")

        if player.media_list.count() > 0:
            player.ml_player.play()
