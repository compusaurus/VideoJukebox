# save as check_vlc_env.py and run: python check_vlc_env.py
import os, platform
vlc_base    = r"C:\Program Files\VideoLAN\VLC"
vlc_plugins = os.path.join(vlc_base, "plugins")
os.environ["PATH"]           = vlc_base + ";" + os.environ.get("PATH","")
os.environ["VLC_PLUGIN_PATH"] = vlc_plugins

print("PATH includes VLC base?   ", vlc_base in os.environ["PATH"])
print("VLC_PLUGIN_PATH folder?   ", os.path.isdir(vlc_plugins))
print("Python architecture:      ", platform.architecture())
try:
    import vlc
    print("python-vlc version:     ", vlc.__version__)
    print("libvlc version:         ", vlc.libvlc_get_version())
    inst = vlc.Instance()
    print("vlc.Instance() returned: ", inst)
    ml   = inst.media_list_new()
    print("media_list_new() =>     ", ml)
except Exception as e:
    print("ERROR loading vlc/medialist:", e)
