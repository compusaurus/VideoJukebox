# vlc_interactive_queue_final.py

import os
import sys
import ctypes
import ctypes.wintypes
import vlc
import tkinter as tk
from tkinter import filedialog

# ─────────────────────────────────────────────────────────────────────────────
# Helper: enumerate all monitors (Win32) so we can place our window on
# the second display (if available).
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
        #  1) Determine the rectangle of the second monitor (if it exists)
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
        #  2) Create a borderless, “full-monitor” Tk window on that display
        # ─────────────────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("VLC Jukebox (Interactive Queue)")
        self.root.overrideredirect(True)  # no title bar or borders
        # Position & size exactly to cover the chosen monitor
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_left}+{self.screen_top}")
        self.root.attributes("-topmost", True)

        # 3) Create a frame to host VLC's video output in that window
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        self.root.update_idletasks()
        self.root.update()
        self.video_window_id = self.video_frame.winfo_id()

        # ─────────────────────────────────────────────────────────────────────
        #  4) Instantiate VLC and build a MediaList + MediaListPlayer
        # ─────────────────────────────────────────────────────────────────────
        self.instance   = vlc.Instance()
        self.media_list = self.instance.media_list_new()
        if not self.media_list:
            print("ERROR: instance.media_list_new() returned None.")
            print("       VLC cannot find its plugins or there's a bitness mismatch.")
            self.root.destroy()
            sys.exit(1)

        self.ml_player = self.instance.media_list_player_new()
        if not self.ml_player:
            print("ERROR: instance.media_list_player_new() returned None.")
            self.root.destroy()
            sys.exit(1)

        self.ml_player.set_media_list(self.media_list)
        self.media_player = self.ml_player.get_media_player()
        if not self.media_player:
            print("ERROR: ml_player.get_media_player() returned None.")
            self.root.destroy()
            sys.exit(1)

        # Embed VLC's video into our Tk frame
        self.media_player.set_hwnd(self.video_window_id)

        # ─────────────────────────────────────────────────────────────────────
        #  5) Overlay “instructions” at the top-left corner
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
        #  6) Bind keys: Escape to quit, 'a' or 'A' to add new files
        # ─────────────────────────────────────────────────────────────────────
        self.root.bind("<Escape>", self._exit_on_escape)
        self.root.bind("<a>", self._on_add)
        self.root.bind("<A>", self._on_add)

        # ─────────────────────────────────────────────────────────────────────
        #  7) Begin polling playback state and enter the Tk main loop
        # ─────────────────────────────────────────────────────────────────────
        self._poll_playback()
        self.root.mainloop()

        # Ensure VLC stops when the window closes
        self.ml_player.stop()

    def _on_add(self, event=None):
        """
        Press 'A' to open a file dialog, pick videos, then append them
        to the VLC playlist. If VLC is idle, automatically start playback.
        """
        # Temporarily turn window decorations back on so the file dialog appears
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", False)

        paths = filedialog.askopenfilenames(
            title="Select video files to enqueue",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("All Files", "*.*")]
        )

        # Restore borderless full-monitor window
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        if not paths:
            return

        enqueued = False
        for path in paths:
            if os.path.isfile(path):
                media = self.instance.media_new(path)
                self.media_list.add_media(media)
                print(f"✅ Enqueued: {path}")
                enqueued = True
            else:
                print(f"⚠️  Skipped (not found): {path}")

        # If VLC is not currently playing, resume playback
        state = self.ml_player.get_state()
        if enqueued and state not in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
            print("▶️  Starting playback of newly enqueued items...")
            self.ml_player.play()

    def _poll_playback(self):
        """
        Every 500 ms, check if VLC is idle (Ended/Stopped) but there are
        still items in the queue—if so, resume playback. Otherwise, wait
        until the user adds more files.
        """
        state = self.ml_player.get_state()
        count = self.media_list.count()
        if state in (vlc.State.Ended, vlc.State.Stopped) and count > 0:
            print("▶️  Resuming playback of queued videos...")
            self.ml_player.play()

        self.root.after(500, self._poll_playback)

    def _exit_on_escape(self, event=None):
        """
        Stop VLC and close the window when the user presses Escape.
        """
        self.ml_player.stop()
        self.root.quit()


if __name__ == "__main__":
    # Optionally accept initial video paths on the command line
    initial_paths = sys.argv[1:]
    player = VLCInteractiveQueue()

    # If the user passed any files on the command line, enqueue them now:
    if initial_paths:
        for p in initial_paths:
            if os.path.isfile(p):
                media = player.instance.media_new(p)
                player.media_list.add_media(media)
                print(f"✅ Enqueued on start: {p}")

        # If at least one was enqueued, start playback immediately
        if player.media_list.count() > 0:
            player.ml_player.play()
