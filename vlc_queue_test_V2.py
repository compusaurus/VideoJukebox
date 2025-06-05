# vlc_queue_test.py
import sys
import os
import time
import vlc
import tkinter as tk

def main(video_paths):
    """
    video_paths: list of filesystem paths to video files you want to queue.
    """

    # ---------------------------------------------------------
    # 1) Build a single Tkinter window and force it to full screen
    # ---------------------------------------------------------
    root = tk.Tk()
    root.title("VLC Jukebox (Full‐Screen)")
    # Remove window decorations (optional) and make full‐screen:
    root.attributes("-fullscreen", True)

    # Create a frame that will hold the VLC video surface
    video_frame = tk.Frame(root, bg="black")
    video_frame.pack(fill=tk.BOTH, expand=True)

    # Force an update so that winfo_id() returns a valid handle
    root.update_idletasks()
    root.update()

    # Grab the native window handle (HWND on Windows; XID on Linux)
    video_window_id = video_frame.winfo_id()

    # ---------------------------------------------------------
    # 2) Create a VLC Instance and its MediaList + MediaListPlayer
    # ---------------------------------------------------------
    # On Windows, no extra flags are needed for full‐screen embedding.
    instance = vlc.Instance()

    # Create the MediaList (this will hold our queued videos)
    media_list = instance.media_list_new()
    if media_list is None:
        print("ERROR: instance.media_list_new() returned None. "
              "Check your VLC_PLUGIN_PATH / PATH so VLC can find its plugins.")
        root.destroy()
        sys.exit(1)

    # Create a MediaListPlayer and attach the MediaList we just made
    ml_player = instance.media_list_player_new()
    if ml_player is None:
        print("ERROR: instance.media_list_player_new() returned None.")
        root.destroy()
        sys.exit(1)

    ml_player.set_media_list(media_list)

    # Grab the underlying MediaPlayer so we can embed its video output
    media_player = ml_player.get_media_player()
    if media_player is None:
        print("ERROR: ml_player.get_media_player() returned None.")
        root.destroy()
        sys.exit(1)

    # Tell VLC to render video into our Tkinter frame (by HWND/XID)
    media_player.set_hwnd(video_window_id)
    # ─ If you’re on Linux/X11, you would instead do:
    # media_player.set_xwindow(video_window_id)
    # ─ On macOS it would be:
    # media_player.set_nsobject(video_window_id)

    # ---------------------------------------------------------
    # 3) Enqueue each video path into our MediaList
    # ---------------------------------------------------------
    for path in video_paths:
        if not os.path.isfile(path):
            print(f"⚠️  File not found, skipping: {path}")
            continue

        media = instance.media_new(path)
        media_list.add_media(media)
        print(f"✅ Enqueued: {path}")

    # ---------------------------------------------------------
    # 4) Start playback if we have at least one valid item
    # ---------------------------------------------------------
    if media_list.count() > 0:
        print("\n▶️  Starting full‐screen playback of queued videos...")
        ml_player.play()
    else:
        print("❌ No valid videos were enqueued. Exiting.")
        root.destroy()
        sys.exit(0)

    # ---------------------------------------------------------
    # 5) Monitor playback: once done, close the window & exit
    # ---------------------------------------------------------
    def _poll_playback():
        state = ml_player.get_state()

        # When state is Ended or Stopped AND there are no more items left,
        # terminate the main loop (which will close the window).
        if (state in (vlc.State.Ended, vlc.State.Stopped)) and (media_list.count() == 0):
            root.quit()
        else:
            # Poll again in 500 ms
            root.after(500, _poll_playback)

    # Kick off our polling function
    root.after(500, _poll_playback)

    # ---------------------------------------------------------
    # 6) Bind <Escape> so that pressing Esc will exit full‐screen & quit
    # ---------------------------------------------------------
    def _exit_on_escape(event=None):
        ml_player.stop()
        root.quit()

    root.bind("<Escape>", _exit_on_escape)

    # Start the Tkinter main loop (blocks until root.quit() is called)
    root.mainloop()

    # Once mainloop exits, ensure VLC stops
    ml_player.stop()
    print("✅ Playback finished. Exiting.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vlc_queue_test.py path/to/video1.mp4 [path/to/video2.mp4 ...]")
        sys.exit(1)

    # Pass all command-line args (after the script name) as video paths
    main(sys.argv[1:])
