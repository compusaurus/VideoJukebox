# vlc_interactive_queue_V5.py

import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# 0) MAKE SURE THIS BLOCK is literally the first lines of the file, 
#    so that Python sees these environment changes BEFORE any 'import vlc'.
# ─────────────────────────────────────────────────────────────────────────────
vlc_base    = r"C:\Program Files\VideoLAN\VLC"
vlc_plugins = os.path.join(vlc_base, "plugins")

# Prepend VLC root to PATH:
os.environ["PATH"] = vlc_base + ";" + os.environ.get("PATH", "")

# Tell libVLC where to find its plugins:
os.environ["VLC_PLUGIN_PATH"] = vlc_plugins

# ─────────────────────────────────────────────────────────────────────────────
# Now it is safe to import python-vlc, because the environment is already set.
# ─────────────────────────────────────────────────────────────────────────────
import vlc
import ctypes
import ctypes.wintypes
import tkinter as tk
from tkinter import filedialog

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
        return 1
    user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(_callback), 0)
    return rects

class VLCInteractiveQueue:
    def __init__(self):
        # 1) Find second monitor (if present)
        monitors = get_monitor_rects()
        if len(monitors) >= 2:
            left, top, right, bottom = monitors[1]
        else:
            left, top, right, bottom = monitors[0]
        self.screen_width  = right - left
        self.screen_height = bottom - top
        self.screen_left   = left
        self.screen_top    = top

        # 2) Create a borderless Tk window that exactly covers that monitor
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_left}+{self.screen_top}")
        self.root.attributes("-topmost", True)

        # 3) Create a frame to embed VLC’s video output
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        self.root.update_idletasks()
        self.root.update()
        self.video_window_id = self.video_frame.winfo_id()

        # 4) Instantiate VLC and create playlist objects
        self.instance   = vlc.Instance()                  # Now libVLC can find its DLLs + plugins
        self.media_list = self.instance.media_list_new()
        if not self.media_list:
            print("ERROR: media_list_new() returned None. Check your PATH / VLC_PLUGIN_PATH.")
            self.root.destroy()
            sys.exit(1)

        self.ml_player = self.instance.media_list_player_new()
        if not self.ml_player:
            print("ERROR: media_list_player_new() returned None.")
            self.root.destroy()
            sys.exit(1)

        self.ml_player.set_media_list(self.media_list)
        self.media_player = self.ml_player.get_media_player()
        if not self.media_player:
            print("ERROR: media_player_new() returned None.")
            self.root.destroy()
            sys.exit(1)

        # Embed VLC’s video into that frame
        self.media_player.set_hwnd(self.video_window_id)

        # 5) Overlay instructions
        inst_lbl = tk.Label(self.root,
            text="Esc: Exit   |   A: Add Videos",
            bg="black", fg="white", font=("Segoe UI", 12)
        )
        inst_lbl.place(x=10, y=10)

        # 6) Bind keys
        self.root.bind("<Escape>", self._exit_on_escape)
        self.root.bind("<a>", self._on_add)
        self.root.bind("<A>", self._on_add)

        # 7) Start polling and run Tk loop
        self._poll_playback()
        self.root.mainloop()
        self.ml_player.stop()

    def _on_add(self, event=None):
        # Temporarily allow decorations so file dialog appears
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", False)

        paths = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("All Files", "*.*")]
        )

        # Return to full‐screen, borderless
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
                print(f"⚠️  Skipped: {p}")

        state = self.ml_player.get_state()
        if enqueued and state not in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
            print("▶️  Starting playback…")
            self.ml_player.play()

    def _poll_playback(self):
        state = self.ml_player.get_state()
        count = self.media_list.count()
        if state in (vlc.State.Ended, vlc.State.Stopped) and count > 0:
            print("▶️  Resuming playback…")
            self.ml_player.play()
        self.root.after(500, self._poll_playback)

    def _exit_on_escape(self, event=None):
        self.ml_player.stop()
        self.root.quit()


if __name__ == "__main__":
    initial = sys.argv[1:]
    player = VLCInteractiveQueue()
    if initial:
        for p in initial:
            if os.path.isfile(p):
                m = player.instance.media_new(p)
                player.media_list.add_media(m)
                print(f"✅ Enqueued on start: {p}")
        if player.media_list.count() > 0:
            player.ml_player.play()
