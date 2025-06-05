# vlc_interactive_queue_V9.py

import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Step 0: FORCE the correct VLC paths into this process BEFORE any `import vlc`.
#
#   Adjust these two paths if VLC lives somewhere else:
#     vlc_base    = r"C:\Program Files\VideoLAN\VLC"
#     vlc_plugins = os.path.join(vlc_base, "plugins")
# ─────────────────────────────────────────────────────────────────────────────

vlc_base    = r"C:\Program Files\VideoLAN\VLC"
vlc_plugins = os.path.join(vlc_base, "plugins")

# 0A) Prepend VLC’s folder (where libvlc.dll lives) to the OS PATH:
os.environ["PATH"] = vlc_base + ";" + os.environ.get("PATH", "")

# 0B) Tell libVLC where its 'plugins' folder is:
os.environ["VLC_PLUGIN_PATH"] = vlc_plugins

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Debug prints to show EXACTLY what our environment looks like now.
#         If these prints don’t match your expectations, libVLC will fail.
# ─────────────────────────────────────────────────────────────────────────────

print(">>> [Debug] After setting env vars:")
print("    PATH starts with:", os.environ["PATH"][:len(vlc_base) + 5], "…")
print("    VLC_PLUGIN_PATH:", os.environ["VLC_PLUGIN_PATH"])
print("    Checking that these folders exist on disk:")
print("      •", vlc_base, "→", os.path.isdir(vlc_base))
print("      •", vlc_plugins, "→", os.path.isdir(vlc_plugins))
print("    Python architecture:", sys.version)
print()

# Now that the environment is correct, import python-vlc:
import ctypes
import ctypes.wintypes
import vlc
import tkinter as tk
from tkinter import filedialog

# ─────────────────────────────────────────────────────────────────────────────
# Helper to enumerate all monitors on Windows so we can place our window
# on the second display. If you only have one display, it falls back to that.
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
        # 1) Pick the second monitor rect (if available), else primary
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
        # 2) Build a borderless, “cover‐that‐monitor” Tk window
        # ─────────────────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("VLC Jukebox (Interactive Queue)")
        self.root.overrideredirect(True)  # no title bar, no borders
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+{self.screen_left}+{self.screen_top}")
        self.root.attributes("-topmost", True)

        # 3) Create a frame inside which VLC will render its video
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        self.root.update_idletasks()
        self.root.update()
        self.video_window_id = self.video_frame.winfo_id()

        # ─────────────────────────────────────────────────────────────────────
        # 4) Instantiate VLC: now that PATH/VLC_PLUGIN_PATH are correct,
        #    libVLC can locate libvlc.dll _and_ its plugins (including playlist).
        # ─────────────────────────────────────────────────────────────────────
        print(">>> [Debug] Attempting vlc.Instance()…")
        try:
            self.instance = vlc.Instance()
            print("    vlc.Instance succeeded:", self.instance)
        except Exception as e:
            print("    ERROR: vlc.Instance() threw →", e)
            sys.exit(1)

        # Test whether libVLC can load the playlist plugin:
        ml_test = self.instance.media_list_new()
        print(">>> [Debug] instance.media_list_new() →", ml_test)
        if ml_test is None:
            print()
            print("ERROR: media_list_new() returned None.")
            print("  → That means libVLC could not load the 'playlist' plugin.")
            print("  → Double‐check that VLC_PLUGIN_PATH and PATH point to the correct folders.")
            self.root.destroy()
            sys.exit(1)
        else:
            print("    🎉 media_list_new() succeeded!")

        # Now continue with the normal construction:
        self.media_list = ml_test
        self.ml_player  = self.instance.media_list_player_new()
        if not self.ml_player:
            print("ERROR: media_list_player_new() returned None.")
            self.root.destroy()
            sys.exit(1)

        self.ml_player.set_media_list(self.media_list)
        self.media_player = self.ml_player.get_media_player()
        if not self.media_player:
            print("ERROR: get_media_player() returned None.")
            self.root.destroy()
            sys.exit(1)

        # Embed VLC’s video into our Tk frame:
        self.media_player.set_hwnd(self.video_window_id)

        # ─────────────────────────────────────────────────────────────────────
        # 5) Draw a small overlay (“Esc: Exit | A: Add Videos”) in top-left
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
        #      • <Escape> → stop & exit  
        #      • “A” / “a” → open file dialog to enqueue more files
        # ─────────────────────────────────────────────────────────────────────
        self.root.bind("<Escape>", self._exit_on_escape)
        self.root.bind("<a>", self._on_add)
        self.root.bind("<A>", self._on_add)

        # ─────────────────────────────────────────────────────────────────────
        # 7) Begin polling VLC’s playback state; then enter the Tk mainloop
        # ─────────────────────────────────────────────────────────────────────
        self._poll_playback()
        self.root.mainloop()
        self.ml_player.stop()

    def _on_add(self, event=None):
        # Temporarily restore window decorations so file dialog appears
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", False)

        paths = filedialog.askopenfilenames(
            title="Select video files to enqueue",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("All Files", "*.*")]
        )

        # Restore borderless full-screen
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
