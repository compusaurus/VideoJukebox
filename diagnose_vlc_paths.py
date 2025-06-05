# diagnose_vlc_paths.py

import os
import platform
import ctypes
import ctypes.wintypes

# 0) Hard-coded paths (adjust if your VLC is installed elsewhere)
vlc_base    = r"C:\Program Files\VideoLAN\VLC"
vlc_plugins = os.path.join(vlc_base, "plugins")

# 0A) Prepend VLC folder to PATH
path_env = os.environ.get("PATH", "")
if vlc_base not in path_env:
    os.environ["PATH"] = vlc_base + ";" + path_env

# 0B) Set VLC_PLUGIN_PATH
os.environ["VLC_PLUGIN_PATH"] = vlc_plugins

print("----- ENVIRONMENT BEFORE IMPORT VLC -----")
print("PATH (first 200 chars):", os.environ["PATH"][:200], "…")
print("VLC_PLUGIN_PATH:", os.environ["VLC_PLUGIN_PATH"])
print("Python architecture:", platform.architecture())
try:
    import vlc
    print("python-vlc version:", vlc.__version__)
    print("libvlc version:", vlc.libvlc_get_version())
except Exception as e:
    print("ERROR: import vlc failed →", e)
    exit(1)

# Try Instance without any flags
try:
    inst = vlc.Instance([])
    print("vlc.Instance([]) returned:", inst)
except Exception as e:
    print("Exception calling vlc.Instance([]) →", e)
    inst = None

if inst:
    ml = inst.media_list_new()
    print("inst.media_list_new() returned:", ml)
    mp = inst.media_player_new()
    print("inst.media_player_new() returned:", mp)
    mlp = inst.media_list_player_new()
    print("inst.media_list_player_new() returned:", mlp)
    inst.release()
