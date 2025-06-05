import vlc
import sys

try:
    inst = vlc.Instance()
except Exception as e:
    print("Failed to load libVLC:", e)
    sys.exit(1)

if inst is None:
    print("vlc.Instance() returned None. That means it couldn’t find the VLC shared library.")
    sys.exit(1)
else:
    print("✅ libVLC loaded successfully (instance is not None).")
