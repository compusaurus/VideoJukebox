# vlc_queue_test.py
import sys
import os
import time
import ctypes
import ctypes.wintypes
import vlc
import tkinter as tk

def get_monitor_rects():
    """
    Returns a list of monitor rectangles [(left, top, right, bottom), ...]
    using the Win32 EnumDisplayMonitors API.
    """
    user32 = ctypes.windll.user32

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.wintypes.HMONITOR,
        ctypes.wintypes.HDC,
        ctypes.POINTER(ctypes.wintypes.RECT),
        ctypes.c_double
    )

    monitor_rects = []

    def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        r = lprcMonitor.contents
        monitor_rects.append((r.left, r.top, r.right, r.bottom))
        return 1  # continue enumeration

    user32.EnumDisplayMonitors(
        0,
        0,
        MonitorEnumProc(_callback),
        0
    )
    return monitor_rects

def main(video_paths):
    """
    video_paths: list of filesystem paths to video files to queue.
    """

    # ---------------------------------------------------------
    # 1) Determine the rectangle of the second monitor (if present)
    # ---------------------------------------------------------
    monitors = get_monitor_rects()
    if len(monitors) < 2:
        # Fallback to primary if no second monitor detected:
        left, top, right, bottom = monitors[0]
    else:
        # Use the second monitor’s rectangle
        left, top, right, bottom = monitors[1]

    # Compute width/height of that monitor:
    screen_width  = right - left
    screen_height = bottom - top

    # ---------------------------------------------------------
    # 2) Build a borderless Tkinter window and position it exactly
    #    over the second monitor
    # ---------------------------------------------------------
    root = tk.Tk()
    root.title("VLC Jukebox (Second Monitor)")

    # Remove window decorations (no title bar, no borders)
    root.overrideredirect(True)

    # Resize & position: "<width>x<height>+<x>+<y>"
    root.geometry(f"{screen_width}x{screen_height}+{left}+{top}")

    # Set window on top (optional, but ensures VLC is visible)
    root.attributes("-topmost", True)

    # Create a frame that will fill that entire area
    video_frame = tk.Frame(root, bg="black")
    video_frame.pack(fill=tk.BOTH, expand=True)

    # Force an update so that winfo_id() is valid
    root.update_idletasks()
    root.update()

    # Grab the window handle (HWND) of our frame
    video_window_id = video_frame.winfo_id()

    # ---------------------------------------------------------
    # 3) Create the VLC Instance and its MediaList + MediaListPlayer
    # ---------------------------------------------------------
    instance = vlc.Instance()

    media_list = instance.media_list_new()
    if media_list is None:
        print("ERROR: instance.media_list_new() returned None.")
        root.destroy()
        sys.exit(1)

    ml_player = instance.media_list_player_new()
    if ml_player is None:
        print("ERROR: instance.media_list_player_new() returned None.")
        root.destroy()
        sys.exit(1)

    ml_player.set_media_list(media_list)

    # Grab the underlying MediaPlayer and tell it to render into our frame
    media_player = ml_player.get_media_player()
    if media_player is None:
        print("ERROR: ml_player.get_media_player() returned None.")
        root.destroy()
        sys.exit(1)

    media_player.set_hwnd(video_window_id)
    # ─ On Linux: media_player.set_xwindow(video_window_id)
    # ─ On macOS: media_player.set_nsobject(video_window_id)

    # ---------------------------------------------------------
    # 4) Enqueue each video path
    # ---------------------------------------------------------
    for path in video_paths:
        if not os.path.isfile(path):
            print(f"⚠️  File not found, skipping: {path}")
            continue
        media = instance.media_new(path)
        media_list.add_media(media)
        print(f"✅ Enqueued: {path}")

    # ---------------------------------------------------------
    # 5) Start playback if there’s at least one file
    # ---------------------------------------------------------
    if media_list.count() > 0:
        print("\n▶️  Starting playback on second monitor...")
        ml_player.play()
    else:
        print("❌ No valid videos were enqueued. Exiting.")
        root.destroy()
        sys.exit(0)

    # ---------------------------------------------------------
    # 6) Poll playback state; when done, close and exit
    # ---------------------------------------------------------
    def _poll_playback():
        state = ml_player.get_state()
        if (state in (vlc.State.Ended, vlc.State.Stopped)) and (media_list.count() == 0):
            root.quit()
        else:
            root.after(500, _poll_playback)

    root.after(500, _poll_playback)

    # Allow pressing ESC to stop early
    def _exit_on_escape(event=None):
        ml_player.stop()
        root.quit()

    root.bind("<Escape>", _exit_on_escape)

    # Start the Tkinter loop (blocks until root.quit())
    root.mainloop()

    # After the window closes, stop VLC
    ml_player.stop()
    print("✅ Playback finished. Exiting.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vlc_queue_test.py path/to/video1.mp4 [path/to/video2.mp4 ...]")
        sys.exit(1)

    main(sys.argv[1:])
