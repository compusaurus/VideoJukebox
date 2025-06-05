# video_jukebox/main.py
import os
import sys
# ENSURE THIS PATH IS CORRECT FOR YOUR VLC INSTALLATION
# This should point to the directory containing libvlc.dll, libvlccore.dll, and the plugins folder
vlc_base = r"C:\Program Files\VideoLAN\VLC" # ADJUST IF YOUR VLC IS ELSEWHERE
vlc_plugins = os.path.join(vlc_base, "plugins")

if not os.path.isdir(vlc_base):
    print(f"ERROR: VLC base directory not found: {vlc_base}")
    print("Please adjust 'vlc_base' in main.py to your VLC installation path.")
    # Optionally, allow user to browse for it or exit
    # For now, we'll let it proceed and python-vlc might still find it if in PATH
    # but this explicit setup is more robust.
else:
    os.environ["PATH"] = vlc_base + os.pathsep + os.environ.get("PATH", "")
    if os.path.isdir(vlc_plugins):
        os.environ["VLC_PLUGIN_PATH"] = vlc_plugins
    else:
        print(f"WARNING: VLC plugins directory not found: {vlc_plugins}")
# (Optional) Debug prints from the example, can be removed later
print(">>> [Debug] After setting env vars:")
print("    PATH relevant part:", os.environ.get("PATH", "")[:len(vlc_base) + 10], "…")
if "VLC_PLUGIN_PATH" in os.environ:
    print("    VLC_PLUGIN_PATH:", os.environ["VLC_PLUGIN_PATH"])
else:
    print("    VLC_PLUGIN_PATH: NOT SET (plugins folder might be missing)")
print("    Checking that these folders exist on disk:")
print("      •", vlc_base, "→", os.path.isdir(vlc_base))
print("      •", vlc_plugins, "→", os.path.isdir(vlc_plugins))
print("    Python architecture:", sys.version) # or platform.architecture()
print()
# ─────────────────────────────────────────────────────────────────────────────
import atexit
import tkinter as tk
from tkinter import Menu, messagebox, simpledialog
# Use screeninfo to get monitor details
try:
    import screeninfo
except ImportError:
    screeninfo = None
    print("screeninfo library not found. Dual display positioning might be basic.")
    print("Install it with: pip install screeninfo")

import logging
import vlc
from core.logger_setup import setup_logging
from core.settings_manager import SettingsManager
from core.credit_manager import CreditManager
from core.queue_manager import QueueManager
from core.music_library import MusicLibrary
from core.video_player import VideoPlayer
from ui.preferences_dialog import PreferencesDialog
from ui.splash_screen import SplashScreen # 
from ui.player_ui import PlayerUI
from ui.main_ui import MainUI # 
# from ui.management_dialog import ManagementDialog # Placeholder

class VideoJukeboxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Jukebox Control")
        # self.root.withdraw() # Consider withdrawing if main_ui is primary

        self.main_ui_window = None
        self.main_ui = None       # Instance of MainUI
        self.player_window = None
        self.player_ui = None     # Instance of PlayerUI
        atexit.register(self.cleanup_on_python_exit)

        self.settings_manager = SettingsManager()
        self.logger = setup_logging(self.settings_manager) # SETUP LOGGING EARLY
        self.logger.info("Application starting...")        
        self.credit_manager = CreditManager(self.settings_manager, initial_credits=20)
        self.music_library = MusicLibrary(self.settings_manager) # music_library is created
        self.queue_manager = QueueManager(self.credit_manager, self.music_library)

        self.video_player = VideoPlayer(self.settings_manager, 
                                        on_media_list_player_event=self.handle_vlc_playlist_event)

        if self.settings_manager.get("show_splash_on_startup"):
            self.show_splash()
        else:
            self.initialize_app_ui() # Renamed from initialize_app

        menubar = Menu(root)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Preferences", command=self.open_preferences)
        filemenu.add_command(label="Management", command=self.open_management_interface_event)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_exit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)
        self.logger.info(f"Menu configured for root window: {self.root}") 
        self.root.geometry("300x100+50+50") # Small control window
        self.root.bind("<Control-Alt-m>", self.open_management_interface_event)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit) # Handle main control window close

    def show_splash(self):
        splash_path = os.path.join(
            self.settings_manager.get("splash_directory"),
            self.settings_manager.get("splash_image_file")
        )
        # Check if custom splash image exists, if not, try default
        if not os.path.exists(splash_path):
            self.logger.warning(f"Custom splash image not found: {splash_path}. Trying default.")
            default_splash_path = os.path.join(os.getcwd(), "assets", "default_splash.jpg") # Assuming assets is in root
            if os.path.exists(default_splash_path):
                splash_path = default_splash_path
            else:
                self.logger.error(f"Splash image not found: {splash_path} and no default_splash.jpg in assets.")
                self.initialize_app_ui() # Skip splash if no image
                return

        # GET THE SPLASH DURATION FROM SETTINGS
        splash_duration = self.settings_manager.get("splash_duration_ms", 3000) # Provide a default if not found

        self.logger.info(f"Showing splash: {splash_path} for {splash_duration}ms")
        self.splash = SplashScreen(self.root, splash_path, splash_duration, self.initialize_app_ui)

    def initialize_app_ui(self): # Renamed
        if hasattr(self, 'splash') and self.splash and self.splash.winfo_exists():
            self.splash.destroy()
            del self.splash

        print("Initializing application UI and components...")
        # self.root.deiconify() # If it was withdrawn
        self.logger.info(f"Attempting to scan music library. Directory from settings: '{self.settings_manager.get('music_video_directory')}'")
        self.music_library.scan_videos() # Scan music library
        self.logger.info(f"Music library scan complete. Number of videos found: {len(self.music_library.videos)}")
        self.setup_displays() # Creates main_ui_window and player_window

        # Now instantiate UI classes with their respective Toplevel windows
        if self.main_ui_window and self.main_ui_window.winfo_exists():
             self.main_ui = MainUI(self.main_ui_window, self) # Pass app instance for callbacks/access
             self.main_ui.refresh_sidebar_lists()
             self.main_ui.load_initial_results()
        else:
            print("Error: Main UI window not available for MainUI class.")

        if self.player_window and self.player_window.winfo_exists():
            self.player_ui = PlayerUI(self.player_window, self.video_player)
        else:
            print("Error: Player window not available for PlayerUI class.")

        self.update_all_ui_elements() # A new method to refresh UIs
        #self.check_queue_and_play()

    def setup_displays(self):
        # ... (monitor detection logic as before) ...
        primary_monitor_geom = (self.root.winfo_screenwidth(), self.root.winfo_screenheight(), 0, 0) # Default
        secondary_monitor_geom = None # Default
        # ... (screeninfo logic from previous version) ...
        monitors = []
        if screeninfo:
            try:
                monitors = screeninfo.get_monitors()
            except screeninfo.common.ScreenInfoError as e:
                print(f"Could not get monitor info: {e}. Assuming single display.")
        
        primary_monitor = None
        secondary_monitor = None

        if monitors:
            # Sort monitors by x-coordinate to ensure consistent ordering if primary flag isn't perfect
            monitors.sort(key=lambda m: m.x) 
            for m in monitors:
                if m.is_primary:
                    primary_monitor = m
                    break # Found primary
            if primary_monitor is None and monitors: # If no primary flag, take first as primary
                primary_monitor = monitors[0]
            
            # Find secondary (first non-primary)
            for m in monitors:
                if m != primary_monitor:
                    secondary_monitor = m
                    break
        
        if primary_monitor:
            primary_monitor_geom = (primary_monitor.width, primary_monitor.height, primary_monitor.x, primary_monitor.y)
            print(f"Primary: {primary_monitor_geom}")
        else: # Fallback
            primary_monitor_geom = (self.root.winfo_screenwidth() // 2, self.root.winfo_screenheight(), 0, 0) # Left half for main UI
            print(f"Primary (fallback): {primary_monitor_geom}")

        if secondary_monitor:
            secondary_monitor_geom = (secondary_monitor.width, secondary_monitor.height, secondary_monitor.x, secondary_monitor.y)
            print(f"Secondary: {secondary_monitor_geom}")
        else: # Fallback if no true secondary, use primary for player too (or a portion)
            w, h, x, y = primary_monitor_geom
            # If only one monitor, place player on the other half, or make it smaller on same screen
            if len(monitors) <= 1:
                 secondary_monitor_geom = (self.root.winfo_screenwidth() // 2, self.root.winfo_screenheight(), self.root.winfo_screenwidth() // 2, 0) # Right half
            else: # Should not happen if primary_monitor_geom is correctly set
                 secondary_monitor_geom = primary_monitor_geom # Default to same if logic error
            print(f"Secondary (fallback): {secondary_monitor_geom}")


        # Create Main UI Window (Touch Screen)
        if not self.main_ui_window or not self.main_ui_window.winfo_exists():
            self.main_ui_window = tk.Toplevel(self.root)
            self.main_ui_window.title("Video Jukebox - User Interface")
            self.main_ui_window.protocol("WM_DELETE_WINDOW", self.on_exit)
            main_w, main_h, main_x, main_y = primary_monitor_geom
            self.main_ui_window.geometry(f"{main_w}x{main_h}+{main_x}+{main_y}")
            # self.main_ui_window.attributes("-fullscreen", True) # For production

        # Create Player Window
        if not self.player_window or not self.player_window.winfo_exists():
            self.player_window = tk.Toplevel(self.root)
            self.player_window.title("Video Jukebox - Playback")
            self.player_window.configure(bg='black')
            self.player_window.protocol("WM_DELETE_WINDOW", lambda: print("Player window close attempted by user.")) # Prevent user close
            play_w, play_h, play_x, play_y = secondary_monitor_geom
            self.player_window.geometry(f"{play_w}x{play_h}+{play_x}+{play_y}")
            # self.player_window.attributes("-fullscreen", True) # For production


    def on_video_end(self, event): # Callback from VLC, triggered by VideoPlayer._handle_media_end
        self.logger.info("App received VLC Event: Video finished playing.")
        if self.main_ui:
            # Clear current song info from the VideoPlayer as well
            if self.video_player:
                self.video_player.current_song_info = None 
                self.video_player.current_media_path = None
            self.main_ui.set_currently_playing(None) # Update UI
        self.check_queue_and_play()

    def old_check_queue_and_play(self):
        self.logger.info("== VideoJukeboxApp.check_queue_and_play CALLED ==")
        
        current_player_state = self.video_player.get_state()
        self.logger.debug(f"Current Player State at start of check_queue_and_play: {current_player_state}")
        
        if current_player_state in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering]:
            self.logger.info(f"Player is busy (state: {current_player_state}). Not fetching next song yet.")
            self.logger.info("== VideoJukeboxApp.check_queue_and_play FINISHED (player busy) ==")
            return

        self.logger.debug("Player not busy. Attempting to get next song from queue.")
        next_song_info = self.queue_manager.get_next_song() 
        
        if next_song_info:
            self.logger.info(f"Next song from queue manager: Artist='{next_song_info.get('artist', 'N/A')}', Title='{next_song_info.get('title', 'N/A')}', Path='{next_song_info.get('path', 'N/A')}'") # Log all details
            self.logger.debug(f"Retrieved next_song_info: {next_song_info}")
            video_path_to_play = next_song_info.get('path') # Use .get() for safety
            if not video_path_to_play:
                self.logger.error(f"!!!!!!!!!! BAD PATH !!!!!!!!! Path is '{video_path_to_play}' for song '{next_song_info.get('title', 'N/A')}'. Attempting to skip to next.")
                #self.logger.error(f"CRITICAL: No 'path' found in next_song_info or path is empty for song: {next_song_info.get('title', 'Unknown title')}. Skipping.")
                if self.on_video_end: # Trigger the same logic as if a video ended with an error
                    self.on_video_end(None) # Pass None as event, it's not used much anyway
                self.logger.info("== VideoJukeboxApp.check_queue_and_play FINISHED (due to bad song path) ==")
                return # IMPORTANT: Exit check_queue_and_play here
            # --- END ADDED LOGGING BLOCK ---
            # This log was already present and confirms next_song_info is not None
            #self.logger.info(f"Playing next song from queue: {next_song_info['artist']} - {next_song_info['title']}") 
            self.logger.info(f"Preparing to play next song: Artist='{next_song_info['artist']}', Title='{next_song_info['title']}' with path='{video_path_to_play}'")
            self.video_player.play(video_path_to_play, song_info=next_song_info) # Use the verified path
            
            if self.player_ui:
                self.player_ui.update_for_new_video() 
            if self.main_ui:
                self.main_ui.set_currently_playing(next_song_info)
                if self.main_ui.is_idle:
                    self.main_ui.exit_idle_mode()
                else: 
                    self.main_ui.reset_idle_timer()
        else:
            self.logger.info("Queue is empty. No new song to play.")
            if self.main_ui:
                self.main_ui.set_currently_playing(None)
                self.main_ui.reset_idle_timer()
        
        self.update_all_ui_elements()
        self.logger.info("== VideoJukeboxApp.check_queue_and_play FINISHED ==")

    def update_all_ui_elements(self):
        if self.main_ui:
            self.main_ui.update_credits_display()
            # Queue display now reads from queue_manager.get_app_queue_view_strings()
            self.main_ui.update_queue_display() 
            # Currently playing is updated by handle_vlc_playlist_event

    def get_vlc_instance(self): # Added for main_ui to access
        return self.video_player.instance if self.video_player else None

    def open_preferences(self):
        # Pass 'self' (the VideoJukeboxApp instance) as the app_controller
        PreferencesDialog(self.root, self.settings_manager, self)

    def open_management_interface_event(self, event=None): # For key binding
        self.open_management_interface()

    def open_management_interface(self):
        password = simpledialog.askstring("Password", "Enter Admin Password:", show='*', parent=self.root)
        if password is None:
            return
        if self.settings_manager.verify_password(password):
            # Check if an instance already exists and is usable
            if not hasattr(self, 'management_dialog_instance') or \
               not self.management_dialog_instance or \
               not self.management_dialog_instance.winfo_exists():
                from ui.management_dialog import ManagementDialog # Import here to avoid circularity if any
                self.management_dialog_instance = ManagementDialog(self.root, self)
            else:
                self.management_dialog_instance.lift() # Bring to front if already open
                self.management_dialog_instance.grab_set() # Ensure it's modal again
                self.management_dialog_instance.load_data_into_tabs() # Refresh data

        else:
            messagebox.showerror("Access Denied", "Incorrect Password.", parent=self.root)

    def trigger_playback_check(self):
        """
        A method that can be called after a song is added to the queue,
        to potentially start playback if nothing is currently playing.
        """
        self.logger.debug("Playback check triggered (e.g., after adding to queue).")
        player_state = self.video_player.get_state()
        if player_state not in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering] and not self.queue_manager.is_empty():
            self.check_queue_and_play()
        elif self.queue_manager.is_empty() and player_state not in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering]:
             if self.main_ui: # If queue is empty and not playing, ensure idle timer resets
                self.main_ui.reset_idle_timer()

    def can_go_idle(self):
        is_active = False
        if self.video_player:
            mlp_state = self.video_player.get_state() # MediaListPlayer's state
            # Active if Playing, Paused (user might resume), Opening, or Buffering
            is_active = mlp_state in [vlc.State.Playing, vlc.State.Paused, 
                                      vlc.State.Opening, vlc.State.Buffering]
        # self.logger.debug(f"can_go_idle: MLP State={mlp_state}, is_active={is_active}")
        return not is_active

    def on_exit(self):
        if messagebox.askokcancel("Quit", "Do you really want to quit Video Jukebox?", parent=self.root):
            self.logger.info("Application exit sequence initiated by user.")
            if self.video_player:
                #self.logger.info("Stopping Playlist and Releasing video player resources...")
                #self.video_player.stop_playlist() # Stop the MediaListPlayer first
                self.video_player.release() 
                self.logger.info("Video player resources released.")
            
            # ... (save settings, self.root.quit(), self.root.destroy()) ...
            self.settings_manager.save_settings() 
            self.logger.info("Quitting Tkinter mainloop.")
            self.root.quit()
            self.root.destroy() 
            self.logger.info("Root window destroyed.")

    def cleanup_on_python_exit(self):
        self.logger.info("ATEEXIT: Cleanup function called.")
        if hasattr(self, 'video_player') and self.video_player:
            self.logger.info("ATEEXIT: video_player object exists. Calling its release() method.")
            try:
                self.video_player.release() # Call the comprehensive release method
                self.logger.info("ATEEXIT: video_player.release() called.")
            except Exception as e:
                self.logger.error(f"ATEEXIT: EXCEPTION during video_player.release(): {e}", exc_info=True)
        else:
            self.logger.info("ATEEXIT: video_player object does not exist or was already None.")
        self.logger.info("ATEEXIT: Cleanup attempt finished.")

    def on_mlp_next_item_set(self, song_info_from_player): 
        # song_info_from_player is what VideoPlayer now derives (e.g., from MRL map or parsing)
        self.logger.info(f"App CB: MediaListPlayer NextItemSet. Song Info: {song_info_from_player.get('title', 'N/A') if song_info_from_player else 'N/A'}")
        
        self.video_player.current_song_info = song_info_from_player # Keep VideoPlayer's current_song_info up to date
                                                                # This is the app's official view of what's playing.
        if self.main_ui:
            self.main_ui.set_currently_playing(song_info_from_player)
            if self.main_ui.is_idle: 
                self.main_ui.exit_idle_mode()
            else: 
                self.main_ui.reset_idle_timer()
        self.update_all_ui_elements() # Update queue display if it needs to reflect a "now playing" change

    def on_mlp_list_played(self):
        self.logger.info("App CB: MediaListPlayer list finished playing or was stopped.")
        self.video_player.current_song_info = None # Clear it
        if self.main_ui:
            self.main_ui.set_currently_playing(None)
            self.main_ui.reset_idle_timer()
        self.update_all_ui_elements()

    def on_mp_error(self): # Error from the underlying MediaPlayer
        self.logger.error("App CB: Core MediaPlayer encountered an error.")
        self.video_player.current_song_info = None # Clear it
        if self.main_ui:
            self.main_ui.set_currently_playing(None)
        # VideoPlayer._handle_mp_error might already try media_list_player.next()
        # So here, we mainly update UI and log.
        self.update_all_ui_elements()

    # OLD on_video_end is no longer directly used by player events for lists
    # def on_video_end(self, event): ... 

    def check_queue_and_play(self):
        self.logger.info("== VideoJukeboxApp.check_queue_and_play (MediaListPlayer Strategy) CALLED ==")
        if not (self.video_player and self.video_player.media_list_player and self.video_player.media_list):
            self.logger.error("App.check_queue_and_play: VideoPlayer components not ready.")
            return

        mlp_state = self.video_player.get_state() # This now gets MediaListPlayer's state
        self.logger.debug(f"App.check_queue_and_play: Current MLP State: {mlp_state}")

        # If already playing, opening, or buffering, do nothing here.
        if mlp_state in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering]:
            self.logger.info(f"App.check_queue_and_play: MLP is busy (state: {mlp_state}). Doing nothing.")
            return

        # If idle/stopped AND the VLC playlist has items, tell it to play.
        if self.video_player.get_playlist_count() > 0:
            self.logger.info("App.check_queue_and_play: VLC MediaList has items. Telling MLP to play.")
            self.video_player.play_playlist() # This calls media_list_player.play()
        else:
            self.logger.info("App.check_queue_and_play: VLC MediaList is empty. Nothing to start.")
            if self.main_ui: self.main_ui.reset_idle_timer()
        
        self.update_all_ui_elements() # Especially the queue display
        self.logger.info("== VideoJukeboxApp.check_queue_and_play (MediaListPlayer Strategy) FINISHED ==")

    def trigger_playback_check(self): # Called after adding a song via UI
        self.logger.debug("App.trigger_playback_check (MediaListPlayer Strategy) called.")
        if not (self.video_player and self.video_player.media_list_player): return

        mlp_state = self.video_player.get_state()
        # If MLP is idle AND there are items in its list, call check_queue_and_play to start it.
        if mlp_state in [vlc.State.NothingSpecial, vlc.State.Stopped, vlc.State.Ended] \
           and self.video_player.get_playlist_count() > 0:
            self.logger.info("App.trigger_playback_check: MLP idle, list has items. Calling check_queue_and_play.")
            self.check_queue_and_play()
        elif self.video_player.get_playlist_count() == 0 and \
             mlp_state not in [vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering]:
            if self.main_ui: self.main_ui.reset_idle_timer() # Ensure idle timer is managed if queue becomes empty

    def handle_vlc_playlist_event(self, event_type, mrl=None):
        self.logger.info(f"App Handling VLC Event: {event_type}, MRL (if any): {mrl}")
        
        current_playing_song_info = None # This will be what we determine is now playing

        if event_type == "NextItemSet":
            if mrl:
                path_from_mrl = self.normalize_mrl_to_path(mrl)
                self.logger.debug(f"NextItemSet: MRL '{mrl}' normalized to path '{path_from_mrl}'")
                
                # Find the song in our library based on the path
                current_playing_song_info = next((s for s in self.music_library.videos if os.path.normpath(s['path']) == path_from_mrl), None)

                if current_playing_song_info:
                    self.logger.info(f"NextItemSet: Mapped MRL to song: {current_playing_song_info['title']}")
                else:
                    self.logger.warning(f"NextItemSet: Could not map path '{path_from_mrl}' to any known song_info.")
                    current_playing_song_info = {"title": "Unknown Track", "artist": "From MRL", "path": path_from_mrl} # Placeholder
            else:
                self.logger.warning("NextItemSet received but MRL is None.")
            
            self.video_player.current_song_info = current_playing_song_info # Update player's tracker

            if self.main_ui:
                self.main_ui.set_currently_playing(current_playing_song_info)
                if current_playing_song_info and self.main_ui.is_idle:
                    self.main_ui.exit_idle_mode()
                else:
                    self.main_ui.reset_idle_timer()
            self.update_all_ui_elements()

        elif event_type == "SingleMediaEnded":
            self.logger.info("App Handling SingleMediaEnded.")
            if mrl:
                path_that_ended = self.normalize_mrl_to_path(mrl)
                self.logger.info(f"Song with path '{path_that_ended}' assumed to have ended.")
                # Pop that track out of the on-screen queue
                self.queue_manager.remove_song_from_app_view(
                    {"path": path_that_ended, "title": "Track that ended"}
                )
            else:
                self.logger.warning("SingleMediaEnded received, but MRL not provided.")

            # We DO NOT call play_playlist() here,
            # because video_player._handle_single_media_ended(…) already removed index 0
            # and immediately started the next item in VLC’s list (if there was one).
            #
            # Instead, just update the UI “Now Playing” text and handle idle if needed:
            if self.video_player.get_playlist_count() == 0:
                self.logger.info("SingleMediaEnded: VLC MediaList is now empty; entering idle.")
                if self.main_ui:
                    self.main_ui.set_currently_playing(None)
                    self.main_ui.reset_idle_timer()

            self.update_all_ui_elements()

        elif event_type == "MediaError":
            # ... (as before)
            if self.main_ui: self.main_ui.set_currently_playing(None)
            self.update_all_ui_elements()
            # Attempt to play next after an error
            if self.video_player.get_playlist_count() > 0:
                self.logger.info("MediaError: Attempting to play next item in playlist.")
                self.video_player.ml_player.next() # Tell MLP to try the next one
            elif self.main_ui: self.main_ui.reset_idle_timer()
        
        elif event_type == "PlaylistEmptyOrEnded": # From our VideoPlayer.play_playlist()
            self.logger.info("App Handling PlaylistEmptyOrEnded event from VideoPlayer.")
            self.video_player.current_song_info = None
            if self.main_ui:
                self.main_ui.set_currently_playing(None)
                self.main_ui.reset_idle_timer()
            self.update_all_ui_elements()

    def normalize_mrl_to_path(self, mrl):
        if not mrl:
            return None
        path = mrl
        if path.startswith('file:///'):
            path = path[8:] # Length of 'file:///'
        
        # URL unquote for spaces etc. Python's urllib.parse.unquote can do this.
        import urllib.parse
        path = urllib.parse.unquote(path)

        # On Windows, if it starts with a single slash then drive letter (e.g., /C:/...), remove leading slash.
        if os.name == 'nt' and len(path) > 2 and path[0] == '/' and path[2] == ':':
            path = path[1:]
        return os.path.normpath(path)
        

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoJukeboxApp(root)
    root.mainloop()
    
  