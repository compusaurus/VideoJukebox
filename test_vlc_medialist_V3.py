import os
import vlc
import platform
import sys

# —–––––––––––––––––––––––––––––––––––––––––––––––––
# 1) FORCE the plugin path (adjust this to your install).
#    If you installed VLC in "C:\Program Files\VideoLAN\VLC",
#    then the plugins will be in "…\VLC\plugins".
# —–––––––––––––––––––––––––––––––––––––––––––––––––
os.environ["VLC_PLUGIN_PATH"] = r"C:\Program Files\VideoLAN\VLC\plugins"

# 2) Print versions
print(f"VLC core version: {vlc.libvlc_get_version()}")
print(f"python-vlc binding version: {vlc.__version__}")

# 3) If you’re on Linux, you can uncomment the next two lines:
# if platform.system() != "Windows":
#     instance_args = ["--no-xlib", "--vout=dummy"]
# else:
instance_args = []

print(f"\nAttempting vlc.Instance({instance_args})…")
try:
    instance = vlc.Instance(instance_args)
    if not instance:
        print("ERROR: vlc.Instance returned None → libVLC could not initialize.")
        sys.exit(1)
    print("✅ vlc.Instance succeeded.")
except Exception as e:
    print("EXCEPTION while creating vlc.Instance:", e)
    sys.exit(1)

print("\nAttempting instance.media_list_new()…")
media_list = instance.media_list_new()
if media_list is None:
    print("❌ FAILURE: instance.media_list_new() returned None.")
    print("  → Your plugin path is probably wrong or unreachable.")
    print("  → Double-check that the folder contains subfolders like 'access', 'codec', 'playlist', etc.")
    instance.release()
    sys.exit(1)
else:
    print(f"✅ SUCCESS: MediaList created → {media_list!r}")
    print(f"    MediaList.count() = {media_list.count()}")
    media_list.release()

print("\nAttempting instance.media_player_new()…")
mp = instance.media_player_new()
if mp is None:
    print("❌ FAILURE: instance.media_player_new() returned None.")
else:
    print(f"✅ SUCCESS: MediaPlayer created → {mp!r}")
    mp.release()

print("\nAttempting instance.media_list_player_new()…")
mlp = instance.media_list_player_new()
if mlp is None:
    print("❌ FAILURE: instance.media_list_player_new() returned None.")
else:
    print(f"✅ SUCCESS: MediaListPlayer created → {mlp!r}")
    mlp.release()

instance.release()
print("\n✅ All done.")
