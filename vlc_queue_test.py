# vlc_queue_test.py
import sys
import os
import time
import vlc

def main(video_paths):
    """
    video_paths: list of filesystem paths to video files you want to queue.
    """

    # 1) Create a bare VLC Instance (no extra args needed on Windows)
    instance = vlc.Instance()

    # 2) Create a MediaList *yourself* and keep a reference to it
    media_list = instance.media_list_new()
    if media_list is None:
        print("ERROR: instance.media_list_new() returned None. Is your VLC_PLUGIN_PATH and PATH set correctly?")
        sys.exit(1)

    # 3) Create a MediaListPlayer
    ml_player = instance.media_list_player_new()
    if ml_player is None:
        print("ERROR: instance.media_list_player_new() returned None.")
        sys.exit(1)

    # 4) Attach YOUR MediaList to the player
    ml_player.set_media_list(media_list)

    # 5) Enqueue each video file into the MediaList
    for path in video_paths:
        if not os.path.isfile(path):
            print(f"⚠️  File not found, skipping: {path}")
            continue

        media = instance.media_new(path)
        media_list.add_media(media)
        print(f"✅ Enqueued: {path}")

    # 6) If the list has at least one item, start playback
    if media_list.count() > 0:
        print("\n▶️  Starting playback of queued videos...")
        ml_player.play()
    else:
        print("❌ No valid videos were enqueued. Exiting.")
        sys.exit(0)

    # 7) Spin until playback is done (or user hits Ctrl-C)
    try:
        while True:
            state = ml_player.get_state()
            # Print state (overwriting the same line)
            print(f"[{time.strftime('%H:%M:%S')}] State: {state}", end="\r")

            # When state is Ended/Stopped AND there are no more items left, exit
            if (state in (vlc.State.Ended, vlc.State.Stopped)) and (media_list.count() == 0):
                break

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping playback early.")
        ml_player.stop()

    print("\n✅ Playback finished. Exiting.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vlc_queue_test.py path/to/video1.mp4 [path/to/video2.mp4 ...]")
        sys.exit(1)

    # Pass all command-line args (after the script name) as video paths
    main(sys.argv[1:])
