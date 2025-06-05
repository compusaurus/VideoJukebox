import vlc
import platform
import sys

print(">>> vlc.libvlc_get_version():", vlc.libvlc_get_version())
print(">>> vlc.__version__ (python-vlc):", vlc.__version__)

# On non‐Windows, try "--no-xlib" (so VLC won’t demand an X display).
instance_args = []
if platform.system() != "Windows":
    instance_args.append("--no-xlib")

print(f"\n>>> Attempting vlc.Instance({instance_args})")
try:
    instance = vlc.Instance(instance_args)
except Exception as e:
    print("   Exception when calling vlc.Instance():", e)
    sys.exit(1)

if instance is None:
    print("   ❌ vlc.Instance(...) returned None. That means libVLC failed to load.")
    print("   → On Windows: ensure that the VLC installation folder (where libvlc.dll lives) is on your %PATH%.")
    print("   → On Linux: ensure that libvlc.so is on your LD_LIBRARY_PATH (or install the distro package `python3-vlc`).")
    print("   → On macOS: make sure DYLD_LIBRARY_PATH includes the path to VLC’s .dylib, or install via Homebrew.")
    sys.exit(1)

print("   ✅ vlc.Instance returned a valid instance object.")

print("\n>>> Attempting instance.media_list_new()")
media_list = instance.media_list_new()
if media_list is None:
    print("   ❌ instance.media_list_new() → None")
else:
    print("   ✅ instance.media_list_new() created:", media_list)
    print("   MediaList.count() =", media_list.count())
    media_list.release()

print("\n>>> Attempting instance.media_player_new()")
mp = instance.media_player_new()
if mp is None:
    print("   ❌ instance.media_player_new() → None")
else:
    print("   ✅ instance.media_player_new() created:", mp)
    mp.release()

print("\n>>> Attempting instance.media_list_player_new()")
mlp = instance.media_list_player_new()
if mlp is None:
    print("   ❌ instance.media_list_player_new() → None")
else:
    print("   ✅ instance.media_list_player_new() created:", mlp)
    mlp.release()

instance.release()
print("\n✅ All done without crashing.")
