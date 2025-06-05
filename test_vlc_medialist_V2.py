# test_vlc_medialist.py (relevant portions) :contentReference[oaicite:0]{index=0}

import vlc
import platform

print(f"VLC version: {vlc.libvlc_get_version()}")
print(f"Python-VLC version: {vlc.__version__}")

instance_args = []
if platform.system() != "Windows":
    instance_args.append("--no-xlib")

print(f"Attempting vlc.Instance({instance_args})...")
instance = vlc.Instance(instance_args)
if not instance:
    print("Failed to create VLC instance (returned None).")
    exit()
print(f"VLC Instance created: {instance}")

print("Attempting instance.media_list_new()...")
media_list = instance.media_list_new()
if media_list:
    print(f"SUCCESS: MediaList created: {media_list}")
    print(f"MediaList current item count: {media_list.count()}")
    media_list.release()
else:
    print("FAILURE: instance.media_list_new() returned None.")

print("Attempting instance.media_player_new()...")
mp = instance.media_player_new()
if mp:
    print(f"SUCCESS: MediaPlayer created: {mp}")
    mp.release()
else:
    print("FAILURE: instance.media_player_new() returned None.")

print("Attempting instance.media_list_player_new()...")
mlp = instance.media_list_player_new()
if mlp:
    print(f"SUCCESS: MediaListPlayer created: {mlp}")
    mlp.release()
else:
    print("FAILURE: instance.media_list_player_new() returned None.")

instance.release()
print("Test finished.")
