# video_jukebox/ui/management_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, Listbox
import re
import os

class ManagementDialog(tk.Toplevel):
    def __init__(self, parent, app_controller):
        super().__init__(parent)
        self.app = app_controller
        self.settings = app_controller.settings_manager
        
        self.title("Management Interface")
        self.geometry("800x600") # Decent size for management
        self.grab_set() # Make it modal
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- Styling (can inherit or define new ones) ---
        self.style = ttk.Style(self) # Get style from this window
        self.style.theme_use('clam') # Consistent theme
        # Add specific styles if needed for management dialog

        # --- Main Notebook for Tabs ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # --- Tab 1: Queue Management ---
        self.queue_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.queue_tab, text="Queue")
        self._create_queue_management_tab(self.queue_tab)

        # --- Tab 2: Credit Management ---
        self.credits_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.credits_tab, text="Credits")
        self._create_credits_management_tab(self.credits_tab)

        # --- Tab 3: Music Library Rules ---
        self.rules_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.rules_tab, text="Music Rules")
        self._create_music_rules_tab(self.rules_tab)
        
        # --- Tab 4: System Settings (subset of preferences) ---
        self.system_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.system_tab, text="System")
        self._create_system_tab(self.system_tab)

        # --- Close Button ---
        close_button = ttk.Button(self, text="Close Management", command=self.on_close)
        close_button.pack(pady=10)

        self.load_data_into_tabs()


    def _create_queue_management_tab(self, tab):
        ttk.Label(tab, text="Current Playback Queue:", font=("Segoe UI", 14, "bold")).pack(pady=10, anchor="w")
        
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.queue_manage_listbox = Listbox(list_frame, font=("Segoe UI", 11), height=15, selectmode=tk.SINGLE) # Now Listbox is defined
        #self.queue_manage_listbox = Listbox(list_frame, font=("Segoe UI", 11), height=15, selectmode=tk.SINGLE)
        # Add scrollbar
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.queue_manage_listbox.yview)
        self.queue_manage_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.queue_manage_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=10)

        remove_button = ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected_from_queue)
        remove_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = ttk.Button(button_frame, text="Clear Entire Queue", command=self.clear_entire_queue)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        skip_button = ttk.Button(button_frame, text="Skip Current Song", command=self.skip_current_song)
        skip_button.pack(side=tk.LEFT, padx=5)


    def _create_credits_management_tab(self, tab):
        ttk.Label(tab, text="Manage User Credits (Mock System):", font=("Segoe UI", 14, "bold")).pack(pady=10, anchor="w")

        current_balance_frame = ttk.Frame(tab)
        current_balance_frame.pack(fill=tk.X, pady=5)
        ttk.Label(current_balance_frame, text="Current Global Credits:", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        self.mg_current_credits_label = ttk.Label(current_balance_frame, text="0", font=("Segoe UI", 12, "bold"))
        self.mg_current_credits_label.pack(side=tk.LEFT)

        add_credits_frame = ttk.Frame(tab)
        add_credits_frame.pack(fill=tk.X, pady=10)
        ttk.Label(add_credits_frame, text="Add Credits:", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        self.add_credits_var = tk.IntVar(value=10)
        add_credits_entry = ttk.Entry(add_credits_frame, textvariable=self.add_credits_var, width=5)
        add_credits_entry.pack(side=tk.LEFT, padx=5)
        add_button = ttk.Button(add_credits_frame, text="Add", command=self.add_credits_action)
        add_button.pack(side=tk.LEFT)

        set_credits_frame = ttk.Frame(tab)
        set_credits_frame.pack(fill=tk.X, pady=10)
        ttk.Label(set_credits_frame, text="Set Total Credits:", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=5)
        self.set_credits_var = tk.IntVar(value=0)
        set_credits_entry = ttk.Entry(set_credits_frame, textvariable=self.set_credits_var, width=5)
        set_credits_entry.pack(side=tk.LEFT, padx=5)
        set_button = ttk.Button(set_credits_frame, text="Set", command=self.set_credits_action)
        set_button.pack(side=tk.LEFT)


    def _create_music_rules_tab(self, tab):
        tab.columnconfigure(0, weight=1) # Column for available items
        tab.columnconfigure(1, weight=1) # Column for action buttons
        tab.columnconfigure(2, weight=1) # Column for blocked items
        tab.rowconfigure(1, weight=1) # Artists row
        tab.rowconfigure(3, weight=1) # Tracks row

        ttk.Label(tab, text="Music Content Restrictions:", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=3, pady=10, sticky="w")

        # --- Artists ---
        ttk.Label(tab, text="Available Artists", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="sw", padx=5)
        ttk.Label(tab, text="Blocked Artists", font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky="sw", padx=5)

        self.all_artists_list = Listbox(tab, selectmode=tk.EXTENDED, exportselection=False)
        self.all_artists_list.grid(row=2, column=0, sticky="nsew", padx=5, pady=2)
        # Add Scrollbar for all_artists_list
        sb_all_artists = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.all_artists_list.yview)
        sb_all_artists.grid(row=2, column=0, sticky="nse", pady=2, padx=(0,5)) # Place next to listbox
        self.all_artists_list.configure(yscrollcommand=sb_all_artists.set)


        artist_buttons_frame = ttk.Frame(tab)
        artist_buttons_frame.grid(row=2, column=1, padx=5, pady=5, sticky="n")
        ttk.Button(artist_buttons_frame, text="Block Sel. >>", command=self.block_selected_artists).pack(pady=3, fill=tk.X)
        ttk.Button(artist_buttons_frame, text="<< Unblock Sel.", command=self.unblock_selected_artists).pack(pady=3, fill=tk.X)
        
        self.manual_artist_var = tk.StringVar()
        ttk.Entry(artist_buttons_frame, textvariable=self.manual_artist_var).pack(pady=(10,3), fill=tk.X)
        ttk.Button(artist_buttons_frame, text="Block Manual", command=self.block_manual_artist).pack(pady=3, fill=tk.X)


        self.blocked_artists_list = Listbox(tab, selectmode=tk.EXTENDED, exportselection=False)
        self.blocked_artists_list.grid(row=2, column=2, sticky="nsew", padx=5, pady=2)
        # Add Scrollbar for blocked_artists_list
        sb_blocked_artists = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.blocked_artists_list.yview)
        sb_blocked_artists.grid(row=2, column=2, sticky="nse", pady=2, padx=(0,5))
        self.blocked_artists_list.configure(yscrollcommand=sb_blocked_artists.set)


        # --- Tracks ---
        ttk.Label(tab, text="Available Tracks (Artist - Title)", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="sw", padx=5, pady=(10,0))
        ttk.Label(tab, text="Blocked Tracks", font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky="sw", padx=5, pady=(10,0))

        self.all_tracks_list = Listbox(tab, selectmode=tk.EXTENDED, exportselection=False)
        self.all_tracks_list.grid(row=4, column=0, sticky="nsew", padx=5, pady=2)
        # Add Scrollbar for all_tracks_list
        sb_all_tracks = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.all_tracks_list.yview)
        sb_all_tracks.grid(row=4, column=0, sticky="nse", pady=2, padx=(0,5))
        self.all_tracks_list.configure(yscrollcommand=sb_all_tracks.set)
        # We need to store paths with these items: self.all_tracks_data = {} # display_text: path


        track_buttons_frame = ttk.Frame(tab)
        track_buttons_frame.grid(row=4, column=1, padx=5, pady=5, sticky="n")
        ttk.Button(track_buttons_frame, text="Block Sel. >>", command=self.block_selected_tracks).pack(pady=3, fill=tk.X)
        ttk.Button(track_buttons_frame, text="<< Unblock Sel.", command=self.unblock_selected_tracks).pack(pady=3, fill=tk.X)
        ttk.Button(track_buttons_frame, text="Block by File...", command=self.block_track_by_file_dialog).pack(pady=(10,3), fill=tk.X)


        self.blocked_tracks_list = Listbox(tab, selectmode=tk.EXTENDED, exportselection=False)
        self.blocked_tracks_list.grid(row=4, column=2, sticky="nsew", padx=5, pady=2)
        # Add Scrollbar for blocked_tracks_list
        sb_blocked_tracks = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.blocked_tracks_list.yview)
        sb_blocked_tracks.grid(row=4, column=2, sticky="nse", pady=2, padx=(0,5))
        self.blocked_tracks_list.configure(yscrollcommand=sb_blocked_tracks.set)
        # Store paths here too: self.blocked_tracks_data = {} # display_text: path

        # Genres: Similar structure if genre metadata exists. For now, omit.

        save_rules_button = ttk.Button(tab, text="Save All Music Rules", command=self.save_music_rules)
        save_rules_button.grid(row=5, column=0, columnspan=3, pady=20)

        # Data dictionaries to map display text to actual data (like paths for tracks)
        self.all_tracks_map = {} # Maps display string to path for all_tracks_list
        self.blocked_tracks_map = {} # Maps display string to path for blocked_tracks_list

    # In load_data_into_tabs():

    def load_data_into_tabs(self):
        # ... (Queue, Credits loading) ...

        # Music Rules
        all_lib_artists = self.app.music_library.get_artists()
        current_blocked_artists = set(s.lower() for s in self.settings.get("blocked_artists", []))

        self.all_artists_list.delete(0, tk.END)
        self.blocked_artists_list.delete(0, tk.END)
        for artist in sorted(all_lib_artists, key=str.lower):
            if artist.lower() not in current_blocked_artists:
                self.all_artists_list.insert(tk.END, artist)
        for blocked_artist in sorted(list(current_blocked_artists), key=str.lower): # Display stored ones
            self.blocked_artists_list.insert(tk.END, blocked_artist.capitalize()) # Show consistently

        # Tracks
        all_lib_videos = self.app.music_library.get_all_videos() # list of dicts
        current_blocked_track_paths = set(self.settings.get("blocked_tracks", []))
        
        self.all_tracks_list.delete(0, tk.END)
        self.blocked_tracks_list.delete(0, tk.END)
        self.all_tracks_map.clear()
        self.blocked_tracks_map.clear()

        # Sort all library videos for consistent display
        all_lib_videos.sort(key=lambda x: (x['artist'].lower(), x['title'].lower()))

        for video_info in all_lib_videos:
            display_text = f"{video_info['artist']} - {video_info['title']}"
            path = video_info['path']
            if path not in current_blocked_track_paths:
                self.all_tracks_list.insert(tk.END, display_text)
                self.all_tracks_map[display_text] = path
            else: # If it is a blocked track path
                self.blocked_tracks_list.insert(tk.END, display_text) # Add to blocked list
                self.blocked_tracks_map[display_text] = path
        
        # Add any paths in settings that might not be in current library scan (e.g. old entries)
        # This part can be complex if a path in settings no longer corresponds to a known artist/title
        # For simplicity now, we only show blocked tracks that are also in the current library scan.
        # A more robust way would be to display the path if artist/title can't be found.


    # --- New methods for Music Rules Tab ---
    def _move_selected_items(self, source_listbox, dest_listbox, source_map=None, dest_map=None):
        selected_indices = source_listbox.curselection()
        if not selected_indices:
            return False
        
        items_to_move = []
        for i in selected_indices:
            items_to_move.append(source_listbox.get(i))
        
        for item_text in items_to_move:
            dest_listbox.insert(tk.END, item_text)
            if source_map and dest_map and item_text in source_map: # Handle track paths
                dest_map[item_text] = source_map[item_text]
                del source_map[item_text]
        
        for i in sorted(selected_indices, reverse=True): # Delete from source
            source_listbox.delete(i)
        return True

    def block_selected_artists(self):
        self._move_selected_items(self.all_artists_list, self.blocked_artists_list)

    def unblock_selected_artists(self):
        self._move_selected_items(self.blocked_artists_list, self.all_artists_list)
    
    def block_manual_artist(self):
        artist_name = self.manual_artist_var.get().strip()
        if artist_name:
            # Check if already in either list to avoid duplicates in UI logic
            if artist_name.lower() not in (a.lower() for a in self.all_artists_list.get(0, tk.END)) and \
               artist_name.lower() not in (a.lower() for a in self.blocked_artists_list.get(0, tk.END)):
                 # If it's a new artist not known to the library, just add to blocked
                 self.blocked_artists_list.insert(tk.END, artist_name)
            else: # If known, move it
                found_in_all = False
                for i, item in enumerate(self.all_artists_list.get(0, tk.END)):
                    if item.lower() == artist_name.lower():
                        self.all_artists_list.delete(i)
                        self.blocked_artists_list.insert(tk.END, item) # Use original casing
                        found_in_all = True
                        break
                if not found_in_all and artist_name.lower() not in (a.lower() for a in self.blocked_artists_list.get(0, tk.END)):
                     self.blocked_artists_list.insert(tk.END, artist_name) # Add if not in blocked

            self.manual_artist_var.set("")
        else:
            messagebox.showwarning("Input Error", "Please enter an artist name.", parent=self)


    def block_selected_tracks(self):
        self._move_selected_items(self.all_tracks_list, self.blocked_tracks_list, 
                                  self.all_tracks_map, self.blocked_tracks_map)

    def unblock_selected_tracks(self):
        self._move_selected_items(self.blocked_tracks_list, self.all_tracks_list,
                                  self.blocked_tracks_map, self.all_tracks_map)

    def block_track_by_file_dialog(self):
        music_dir = self.app.settings_manager.get("music_video_directory") or os.getcwd()
        filepath = filedialog.askopenfilename(
            title="Select Music Video to Block",
            initialdir=music_dir,
            filetypes=(("Video Files", "*.mp4 *.mkv *.avi *.mov"), ("All files", "*.*")),
            parent=self
        )
        if filepath:
            # Try to find this file in the 'all_tracks_list' to move it
            # Or, if not found (e.g. library not scanned yet with this file), add its path directly
            found_in_all_list = False
            for i, item_text in enumerate(self.all_tracks_list.get(0, tk.END)):
                if self.all_tracks_map.get(item_text) == filepath:
                    self.all_tracks_list.delete(i) # Remove from available
                    del self.all_tracks_map[item_text]
                    
                    self.blocked_tracks_list.insert(tk.END, item_text) # Add to UI blocked
                    self.blocked_tracks_map[item_text] = filepath
                    found_in_all_list = True
                    break
            
            if not found_in_all_list:
                # If not in current "all tracks" list, add its path to blocked tracks if not already there
                # We need an artist/title for display. If it's a new file, parse it.
                # This is simpler if we just add the path and let save_music_rules handle it.
                # For UI, we might not have a nice display name yet.
                filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
                artist, title = "Unknown Artist", filename_no_ext # Basic parse
                # This part needs more robust filename parsing like in MusicLibrary
                parts = re.split(r'\s+-\s+', filename_no_ext, 1)
                if len(parts) > 1: artist, title = parts[0].strip(), parts[1].strip()
                elif len(parts) == 1: title = parts[0].strip()

                display_text_for_blocked = f"{artist} - {title}"
                
                # Check if this path is already represented in the blocked_tracks_list
                already_blocked = False
                for path_in_map in self.blocked_tracks_map.values():
                    if path_in_map == filepath:
                        already_blocked = True
                        break
                
                if not already_blocked:
                    self.blocked_tracks_list.insert(tk.END, display_text_for_blocked)
                    self.blocked_tracks_map[display_text_for_blocked] = filepath
                else:
                    messagebox.showinfo("Info", "That track is already in the blocked list.", parent=self)


    def save_music_rules(self):
        new_blocked_artists = [artist.lower() for artist in self.blocked_artists_list.get(0, tk.END)]
        
        new_blocked_track_paths = list(self.blocked_tracks_map.values()) # Get paths from map

        self.settings.set("blocked_artists", new_blocked_artists)
        self.settings.set("blocked_tracks", new_blocked_track_paths)
        # Add genres if implemented: self.settings.set("blocked_genres", new_blocked_genres)
        self.settings.save_settings()
        
        self.app.logger.info(f"Saved music rules. Blocked artists: {len(new_blocked_artists)}, Blocked tracks: {len(new_blocked_track_paths)}")

        if messagebox.askyesno("Rules Saved", "Music rules saved. Re-scan library to apply changes?", parent=self):
            self.rescan_library_action() # This already shows a confirmation
        else:
            messagebox.showinfo("Rules Saved", "Music rules saved. Re-scan library from the main menu or later to apply.", parent=self)
        
        # Refresh lists in case re-scan didn't happen or to reflect current state from settings.
        self.load_data_into_tabs()
    def _create_system_tab(self, tab):
        ttk.Label(tab, text="System Operations & Settings:", font=("Segoe UI", 14, "bold")).pack(pady=10, anchor="w")

        rescan_button = ttk.Button(tab, text="Re-scan Music Library", command=self.rescan_library_action)
        rescan_button.pack(pady=5, fill=tk.X)
        
        change_pass_button = ttk.Button(tab, text="Change Admin Password", command=self.change_admin_password)
        change_pass_button.pack(pady=5, fill=tk.X)

        # Could add sliders for master volume if VLC volume is controllable this way
        # ttk.Label(tab, text="Master Volume:").pack(anchor="w", pady=(10,0))
        # self.volume_scale = ttk.Scale(tab, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_master_volume)
        # self.volume_scale.pack(fill=tk.X, pady=5)
        # self.volume_scale.set(self.app.video_player.get_volume()) # Init with current volume


    def load_data_into_tabs(self):
        # Queue
        self.queue_manage_listbox.delete(0, tk.END)
        for song in self.app.queue_manager.get_full_queue():
            self.queue_manage_listbox.insert(tk.END, f"{song['artist']} - {song['title']}")
        
        # Credits
        self.mg_current_credits_label.config(text=str(self.app.credit_manager.get_balance()))
        self.set_credits_var.set(self.app.credit_manager.get_balance())

        # Music Rules (load from settings)
        self.blocked_artists_list.delete(0, tk.END)
        for artist in self.settings.get("blocked_artists", []):
            self.blocked_artists_list.insert(tk.END, artist)
        # Do similarly for tracks and genres if implemented

    def refresh_ui_data(self):
        """Call this after actions that change underlying data."""
        self.load_data_into_tabs()
        self.app.update_all_ui_elements() # Update main UI as well


    def remove_selected_from_queue(self):
        selected_indices = self.queue_manage_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "No song selected to remove.", parent=self)
            return
        
        # Remove from last to first to keep indices correct
        for index in sorted(selected_indices, reverse=True):
            removed_song = self.app.queue_manager.remove_song(index)
            if removed_song:
                # Note: Credits are not refunded by default on manual removal
                print(f"Admin removed: {removed_song['title']}")
        self.refresh_ui_data()

    def clear_entire_queue(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire queue?", parent=self):
            self.app.queue_manager.clear_queue()
            # Note: Credits are not refunded
            self.refresh_ui_data()
            
    def skip_current_song(self):
        if messagebox.askyesno("Confirm", "Skip the currently playing song?", parent=self):
            self.app.video_player.stop() # This will trigger on_video_end
            # on_video_end will call check_queue_and_play, effectively skipping
            self.refresh_ui_data()


    def add_credits_action(self):
        try:
            amount = self.add_credits_var.get()
            if amount > 0 :
                self.app.credit_manager.add_credits(amount)
                self.refresh_ui_data()
            else:
                messagebox.showerror("Input Error", "Please enter a positive amount.", parent=self)
        except tk.TclError:
            messagebox.showerror("Input Error", "Invalid number for credits.", parent=self)

    def set_credits_action(self):
        try:
            amount = self.set_credits_var.get()
            if amount >= 0:
                self.app.credit_manager.set_balance(amount)
                self.refresh_ui_data()
            else:
                messagebox.showerror("Input Error", "Credits cannot be negative.", parent=self)
        except tk.TclError:
            messagebox.showerror("Input Error", "Invalid number for credits.", parent=self)


    def save_music_rules(self):
        # Example for blocked artists
        # current_blocked_artists_in_ui = list(self.blocked_artists_list.get(0, tk.END))
        # self.settings.set("blocked_artists", current_blocked_artists_in_ui)
        # self.settings.save_settings()
        # self.app.music_library.scan_videos() # Re-scan to apply new rules
        # self.app.main_ui.perform_search() # Refresh search results in main UI
        messagebox.showinfo("Music Rules", "Music rules saving is a TODO. \nRe-scan library if changes were made manually to config.", parent=self)
        self.refresh_ui_data()


    def rescan_library_action(self):
        if messagebox.askyesno("Confirm", "Re-scan the music library? This may take a moment.", parent=self):
            self.app.logger.info("Admin triggered library re-scan.")
            self.app.music_library.scan_videos()
            if self.app.main_ui:
                self.app.main_ui.perform_search() # Clear and potentially repopulate search
                self.app.main_ui.refresh_sidebar_lists() # Add this
            messagebox.showinfo("Library Scan", "Music library re-scan complete.", parent=self)
            self.app.logger.info("Library re-scan complete.")

    def change_admin_password(self):
        current_password = simpledialog.askstring("Current Password", "Enter current admin password:", show='*', parent=self)
        
        # Handle Cancel explicitly
        if current_password is None:
            return # User cancelled, do nothing further

        if not self.settings.verify_password(current_password):
            messagebox.showerror("Error", "Incorrect current password.", parent=self)
            return
        
        new_password1 = simpledialog.askstring("New Password", "Enter new admin password:", show='*', parent=self)
        if new_password1 is None: return # User cancelled
        
        new_password2 = simpledialog.askstring("Confirm Password", "Confirm new admin password:", show='*', parent=self)
        if new_password2 is None: return # User cancelled

        if not new_password1: # Handle empty new password string
            messagebox.showerror("Error", "New password cannot be empty.", parent=self)
            return

        if new_password1 == new_password2:
            self.settings.set_admin_password(new_password1)
            messagebox.showinfo("Success", "Admin password changed successfully.", parent=self)
        else:
            messagebox.showerror("Error", "New passwords do not match.", parent=self)


    def on_close(self):
        self.destroy()