# vlc_queue_test.py
import sys
import os
import time
import vlc

def main(video_paths):
    """
    video_paths: list of filesystem paths to video files you want to queue.
    """

    # 1) Create a bare VLC Instance (no special flags needed on Windows).
    instance = vlc.Instance()

    # 2) Create a MediaListPlayer and grab its internal MediaList
    ml_player = instance.media_list_player_new()
    media_list = ml_player.get_media_list()
    if media_list is None:
        print("ERROR: get_media_list() returned None. Can't queue videos.")
        sys.exit(1)

    # 3) For each video path, create a Media and add it to the MediaList
    for path in video_paths:
        if not os.path.isfile(path):
            print(f"⚠️  File not found, skipping: {path}")
            continue

        media = instance.media_new(path)
        media_list.add_media(media)
        print(f"✅ Enqueued: {path}")

    # 4) If the list has at least 1 video, start playback
    if media_list.count() > 0:
        print("\n▶️  Starting playback of queued videos...")
        ml_player.play()
    else:
        print("❌ No valid videos were enqueued. Exiting.")
        sys.exit(0)

    # 5) Keep the script alive until the entire playlist finishes
    #    (You could instead hook this into a GUI mainloop if embedding.)
    try:
        while True:
            state = ml_player.get_state()
            # Print state for debugging:
            print(f"[{time.strftime('%H:%M:%S')}] State: {state}", end="\r")
            # Once we reach “Ended” and there are no more items, break out
            if state == vlc.State.Ended or state == vlc.State.Stopped:
                # Double-check if playlist is actually over (no items left)
                if media_list.count() == 0 or state == vlc.State.Stopped:
                    break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping playback early.")
        ml_player.stop()

    print("\n✅ Playback finished. Exiting.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vlc_queue_test.py path/to/video1.mp4 [video2.mkv ...]")
        sys.exit(1)

    # Pass all command-line args (after the script name) as video paths
    main(sys.argv[1:])
