# video_jukebox/ui/main_ui.py
import os
import tkinter as tk
from tkinter import ttk, Listbox, Scrollbar, messagebox
from PIL import Image, ImageTk # For album art

# Default image path (relative to where the script is run or a known assets folder)
DEFAULT_ALBUM_ART_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "default_album_art.png")


# video_jukebox/ui/main_ui.py

class MainUI:
    def __init__(self, window, app_controller):
        self.window = window  # This is the Toplevel window for the main UI
        self.app = app_controller  # Reference to VideoJukeboxApp instance
        self.settings = app_controller.settings_manager

        # --- Styling ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        # ... (your style configurations) ...
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TLabel", background="#2E2E2E", foreground="white", font=("Segoe UI", 12))
        self.style.configure("Header.TLabel", font=("Segoe UI Semibold", 16))
        self.style.configure("Credit.TLabel", font=("Segoe UI", 28, "bold"), foreground="#4CAF50")
        self.style.configure("TButton", font=("Segoe UI", 12), padding=10)
        self.style.configure("Search.TButton", font=("Segoe UI", 14, "bold"), background="#2196F3", foreground="white")
        self.style.configure("Queue.TButton", font=("Segoe UI", 14, "bold"), background="#F44336", foreground="white")
        self.style.configure("TEntry", font=("Segoe UI", 12), padding=5)
        self.style.configure("Treeview", font=("Segoe UI", 11), rowheight=25)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))
        self.style.map("Search.TButton", background=[('active', '#1976D2')])
        self.style.map("Queue.TButton", background=[('active', '#D32F2F')])

        # --- Main Layout Frames ---
        self.window.configure(bg="#2E2E2E")

        self.left_panel = ttk.Frame(self.window, width=350, style="TFrame")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.left_panel.pack_propagate(False)

        self.right_panel = ttk.Frame(self.window, style="TFrame")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- LOAD DEFAULT ARTWORK EARLY ---
        self.load_default_album_art()

        # --- Populate Left Panel ---
        self._create_credits_display(self.left_panel)
        self._create_now_playing_display(self.left_panel)
        self._create_queue_snippet_display(self.left_panel)

        # --- Populate Right Panel ---
        self.search_view_frame = ttk.Frame(self.right_panel, style="TFrame")
        self.details_view_frame = ttk.Frame(self.right_panel, style="TFrame")

        self._create_search_view(self.search_view_frame)
        self._create_details_view(self.details_view_frame)

        self.current_selected_song_details = None

        self.show_search_view()
        
        # --- Idle Timer Setup ---
        self.idle_timeout_ms = self.settings.get("idle_timeout_ms", 60000)
        self.idle_timer_id = None
        self.is_idle = False
        self.app.root.after(100, self.reset_idle_timer) 
        
        self.window.bind("<KeyPress>", self.reset_idle_timer_event, add="+")
        self.window.bind("<ButtonPress>", self.reset_idle_timer_event, add="+")
        self.window.bind("<Motion>", self.reset_idle_timer_event, add="+")

        # --- Start Periodic Update ---
        self.window.after(5000, self.periodic_update) # Correct way to start periodic_update

    def load_default_album_art(self):
        try:
            if os.path.exists(DEFAULT_ALBUM_ART_PATH):
                img = Image.open(DEFAULT_ALBUM_ART_PATH)
            else: # Create a fallback black square if default is missing
                print(f"Warning: Default album art not found at {DEFAULT_ALBUM_ART_PATH}. Creating fallback.")
                img = Image.new('RGB', (200, 200), color = 'black')
                # You could draw text on it:
                # from PIL import ImageDraw
                # draw = ImageDraw.Draw(img)
                # draw.text((10,10), "No Art", fill=(255,255,255))

            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            self.default_album_art_tk = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading default album art: {e}")
            # Create a truly minimal fallback if PIL fails badly
            self.default_album_art_tk = None # Or a placeholder Tkinter image

    def _create_credits_display(self, parent):
        frame = ttk.Frame(parent, style="TFrame", padding=10)
        frame.pack(fill=tk.X, pady=(0,10))
        ttk.Label(frame, text="Credits Remaining:", style="Header.TLabel").pack(side=tk.TOP, anchor="w")
        self.credits_label = ttk.Label(frame, text="0", style="Credit.TLabel")
        self.credits_label.pack(side=tk.TOP, anchor="center", pady=5)

    def _create_now_playing_display(self, parent):
        frame = ttk.LabelFrame(parent, text="Currently Playing", style="TFrame", padding=10)
        frame.pack(fill=tk.X, pady=10)
        
        self.now_playing_art_label = ttk.Label(frame, style="TLabel") # For album art
        self.now_playing_art_label.pack(pady=5)
        self.set_album_art(self.now_playing_art_label, None) # Show default initially

        self.now_playing_artist_label = ttk.Label(frame, text="Artist: ---", style="TLabel", wraplength=300)
        self.now_playing_artist_label.pack(anchor="w")
        self.now_playing_title_label = ttk.Label(frame, text="Track: ---", style="TLabel", wraplength=300)
        self.now_playing_title_label.pack(anchor="w")

    def _create_queue_snippet_display(self, parent):
        frame = ttk.LabelFrame(parent, text="Up Next", style="TFrame", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.queue_listbox = Listbox(frame, bg="#424242", fg="white", font=("Segoe UI", 10),
                                     selectbackground="#0078D7", borderwidth=0, highlightthickness=0)
        self.queue_listbox.pack(fill=tk.BOTH, expand=True)
        # No scrollbar for snippet, it's just a peek

    def _create_search_view(self, parent):
        parent.columnconfigure(1, weight=1) # Make entry expand

        # Search Input
        search_bar_frame = ttk.Frame(parent, style="TFrame", padding=(0,0,0,10))
        search_bar_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,10))
        search_bar_frame.columnconfigure(1, weight=1)

        ttk.Label(search_bar_frame, text="Search:", style="Header.TLabel").grid(row=0, column=0, padx=(0,5), sticky="w")
        self.search_entry_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_bar_frame, textvariable=self.search_entry_var, style="TEntry", font=("Segoe UI", 14))
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_button = ttk.Button(search_bar_frame, text="Search", command=self.perform_search, style="Search.TButton")
        self.search_button.grid(row=0, column=2, padx=(10,0), sticky="e")
        self.search_entry.bind("<Return>", lambda event: self.perform_search())

        # Cost/Balance (Mockup style)
        info_frame = ttk.Frame(parent, style="TFrame")
        info_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        self.cost_label = ttk.Label(info_frame, text="Cost: N/A Credits", style="TLabel")
        self.cost_label.pack(side=tk.LEFT, padx=5)
        self.balance_label = ttk.Label(info_frame, text="Balance: N/A Credits", style="TLabel")
        self.balance_label.pack(side=tk.LEFT, padx=5)

        # Results Area (using Treeview for columns)
        results_frame = ttk.Frame(parent, style="TFrame")
        results_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10,0))
        parent.rowconfigure(2, weight=1) # Make results area expand

        columns = ("artist", "title", "cost")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", style="Treeview", selectmode="browse")
        self.results_tree.heading("artist", text="Artist")
        self.results_tree.heading("title", text="Title")
        self.results_tree.heading("cost", text="Cost")
        self.results_tree.column("artist", width=250, anchor="w")
        self.results_tree.column("title", width=350, anchor="w")
        self.results_tree.column("cost", width=80, anchor="center")

        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=vsb.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.results_tree.bind("<<TreeviewSelect>>", self.on_result_selected)
        self.results_tree.bind("<Double-1>", self.on_result_double_clicked)

        # --- Bottom Panels Frame (Artists A-Z / Most Popular) ---
        bottom_panels_frame = ttk.Frame(parent, style="TFrame")
        bottom_panels_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10,0))
        bottom_panels_frame.columnconfigure(0, weight=1)
        bottom_panels_frame.columnconfigure(1, weight=1)

        # Artists A-Z Frame
        artists_az_frame = ttk.LabelFrame(bottom_panels_frame, text="Artists A-Z", style="TFrame")
        artists_az_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        artists_az_frame.rowconfigure(0, weight=1) # Make listbox expand
        artists_az_frame.columnconfigure(0, weight=1)

        self.artists_az_listbox = Listbox(artists_az_frame, bg="#424242", fg="white", height=5,
                                          exportselection=False, selectbackground="#0078D7") # exportselection=False for multiple listboxes
        self.artists_az_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        artist_sb = ttk.Scrollbar(artists_az_frame, orient=tk.VERTICAL, command=self.artists_az_listbox.yview)
        artist_sb.grid(row=0, column=1, sticky="ns")
        self.artists_az_listbox.configure(yscrollcommand=artist_sb.set)
        
        self.artists_az_listbox.bind("<<ListboxSelect>>", self.on_artist_az_selected)
        self.populate_artists_az_list() # New method call

        # Most Popular Frame
        most_popular_frame = ttk.LabelFrame(bottom_panels_frame, text="Suggestions", style="TFrame") # Renamed from Most Popular
        most_popular_frame.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        most_popular_frame.rowconfigure(0, weight=1)
        most_popular_frame.columnconfigure(0, weight=1)

        self.most_popular_listbox = Listbox(most_popular_frame, bg="#424242", fg="white", height=5,
                                            exportselection=False, selectbackground="#0078D7")
        self.most_popular_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        popular_sb = ttk.Scrollbar(most_popular_frame, orient=tk.VERTICAL, command=self.most_popular_listbox.yview)
        popular_sb.grid(row=0, column=1, sticky="ns")
        self.most_popular_listbox.configure(yscrollcommand=popular_sb.set)

        self.most_popular_listbox.bind("<Double-1>", self.on_popular_song_double_clicked) # Use double click to go to details
        self.populate_most_popular_list() # New method call

    def _create_details_view(self, parent):
        parent.pack_propagate(False) # Keep parent size
        parent.columnconfigure(0, weight=1) # Allow content to center or expand if needed
        parent.rowconfigure(3, weight=1) # Give description space

        back_button = ttk.Button(parent, text="< Back to Search", command=self.show_search_view, style="TButton")
        back_button.grid(row=0, column=0, sticky="nw", pady=10, padx=10)

        self.detail_art_label = ttk.Label(parent, style="TLabel") # For album art
        self.detail_art_label.grid(row=1, column=0, pady=10)
        self.set_album_art(self.detail_art_label, None) # Default art

        self.detail_artist_label = ttk.Label(parent, text="Artist: ", style="Header.TLabel")
        self.detail_artist_label.grid(row=2, column=0, pady=(10,0))
        self.detail_title_label = ttk.Label(parent, text="Track: ", style="Header.TLabel")
        self.detail_title_label.grid(row=3, column=0, pady=(0,10))

        self.detail_description_text = tk.Text(parent, wrap=tk.WORD, height=8, bg="#424242", fg="white",
                                               font=("Segoe UI", 11), relief=tk.FLAT, padx=5, pady=5)
        self.detail_description_text.grid(row=4, column=0, sticky="ew", pady=5, padx=10)
        self.detail_description_text.insert(tk.END, "Song description will appear here...")
        self.detail_description_text.config(state=tk.DISABLED) # Read-only

        self.add_to_queue_button = ttk.Button(parent, text="Add to Queue (X Credits)",
                                              command=self.add_selected_to_queue, style="Queue.TButton")
        self.add_to_queue_button.grid(row=5, column=0, pady=20, ipady=10)

    def show_search_view(self):
        self.details_view_frame.pack_forget()
        self.search_view_frame.pack(fill=tk.BOTH, expand=True)
        self.current_selected_song_details = None # Clear selection when going back
        self.update_search_view_balance_cost() # Update cost/balance

    def show_details_view(self, song_details):
        self.current_selected_song_details = song_details
        self.search_view_frame.pack_forget()
        self.details_view_frame.pack(fill=tk.BOTH, expand=True)

        self.detail_artist_label.config(text=f"Artist: {song_details['artist']}")
        self.detail_title_label.config(text=f"Track: {song_details['title']}")
        
        # Placeholder for description and album art
        desc_text = f"'{song_details['title']}' by {song_details['artist']}.\n\n"
        desc_text += "This is a placeholder description. Real applications might fetch this from a database or metadata."
        self.detail_description_text.config(state=tk.NORMAL)
        self.detail_description_text.delete(1.0, tk.END)
        self.detail_description_text.insert(tk.END, desc_text)
        self.detail_description_text.config(state=tk.DISABLED)

        self.add_to_queue_button.config(text=f"Add to Queue ({song_details.get('cost', 'N/A')} Credits)")
        self.set_album_art(self.detail_art_label, song_details.get('path')) # Try to load art

    def set_album_art(self, art_label_widget, video_path, size=(200, 200)):
        loaded_custom_art = False
        if video_path:
            video_dir = os.path.dirname(video_path)
            video_filename_stem = os.path.splitext(os.path.basename(video_path))[0]
            
            # Common art filenames to check
            possible_art_files = [
                os.path.join(video_dir, "cover.jpg"),
                os.path.join(video_dir, "folder.jpg"),
                os.path.join(video_dir, "albumart.jpg"),
                os.path.join(video_dir, f"{video_filename_stem}.jpg"),
                os.path.join(video_dir, "cover.png"),
                os.path.join(video_dir, "folder.png"),
                os.path.join(video_dir, "albumart.png"),
                os.path.join(video_dir, f"{video_filename_stem}.png"),
            ]

            for art_file_path in possible_art_files:
                if os.path.exists(art_file_path):
                    try:
                        img = Image.open(art_file_path)
                        img = img.resize(size, Image.Resampling.LANCZOS)
                        tk_image = ImageTk.PhotoImage(img)
                        art_label_widget.config(image=tk_image)
                        art_label_widget.image = tk_image  # Keep reference
                        loaded_custom_art = True
                        self.app.logger.info(f"Loaded custom album art: {art_file_path}")
                        break 
                    except Exception as e:
                        self.app.logger.error(f"Error loading custom art '{art_file_path}': {e}")
        
        if not loaded_custom_art:
            if self.default_album_art_tk:
                art_label_widget.config(image=self.default_album_art_tk)
                art_label_widget.image = self.default_album_art_tk
            else:
                art_label_widget.config(text="[No Art]", image='')

    def perform_search(self):
        query = self.search_entry_var.get()
        results = self.app.music_library.search(query)
        
        self.results_tree.delete(*self.results_tree.get_children()) # Clear previous results
        if results:
            for song in results:
                self.results_tree.insert("", tk.END, values=(
                    song['artist'], song['title'], song.get('cost', 'N/A')
                ), iid=song['path']) # Use path as unique ID
        else:
            # Maybe insert a "No results found" item or show a label
            pass
        self.update_search_view_balance_cost() # Reset cost display

    def on_result_selected(self, event):
        selected_item = self.results_tree.focus() # Get selected item's IID (path)
        if selected_item:
            # Find the song details from the library using the path
            song_details = next((s for s in self.app.music_library.videos if s['path'] == selected_item), None)
            if song_details:
                self.current_selected_song_details = song_details
                self.update_search_view_balance_cost(song_details.get('cost'))

    def on_result_double_clicked(self, event):
        selected_item_iid = self.results_tree.focus()
        if selected_item_iid:
            # Find the song by its path (IID)
            song_details = next((s for s in self.app.music_library.videos if s['path'] == selected_item_iid), None)
            if song_details:
                self.show_details_view(song_details)

    def add_selected_to_queue(self):
        if self.current_selected_song_details:
            song_to_add = self.current_selected_song_details
            success, message = self.app.queue_manager.add_song(song_to_add) # This deducts credits
            if success:
                self.app.logger.info(f"Song '{song_to_add['title']}' added to queue by user.")
                messagebox.showinfo("Queue Update", message, parent=self.window)
                self.app.update_all_ui_elements() # Update credits and queue display
                
                # CRUCIAL: Trigger a check to see if playback should start
                self.app.trigger_playback_check() 
                
                self.show_search_view() # Optionally go back to search view
            else:
                messagebox.showerror("Queue Error", message, parent=self.window)
        else:
            messagebox.showwarning("Selection Error", "No song selected to add.", parent=self.window)

    def update_credits_display(self):
        credits = self.app.credit_manager.get_balance()
        self.credits_label.config(text=str(credits))
        self.update_search_view_balance_cost() # Update balance in search view too

    def update_search_view_balance_cost(self, cost_of_selected=None):
        balance = self.app.credit_manager.get_balance()
        self.balance_label.config(text=f"Balance: {balance} Credits")
        if cost_of_selected is not None:
            self.cost_label.config(text=f"Cost: {cost_of_selected} Credits")
        else:
            self.cost_label.config(text="Cost: N/A")

    def update_queue_display(self):
        self.queue_listbox.delete(0, tk.END)
        queue_items = self.app.queue_manager.get_queue_view(limit=10) # Show more in snippet
        for item_text in queue_items:
            self.queue_listbox.insert(tk.END, item_text)

    def set_currently_playing(self, song_info):
        if song_info:
            self.now_playing_artist_label.config(text=f"Artist: {song_info['artist']}")
            self.now_playing_title_label.config(text=f"Track: {song_info['title']}")
            self.set_album_art(self.now_playing_art_label, song_info.get('path'))
        else:
            self.now_playing_artist_label.config(text="Artist: ---")
            self.now_playing_title_label.config(text="Track: ---")
            self.set_album_art(self.now_playing_art_label, None)

    # def periodic_update(self):
    #     # Example: self.update_queue_display()
    #     self.window.after(5000, self.periodic_update) # Reschedule
    

    def populate_artists_az_list(self):
        self.artists_az_listbox.delete(0, tk.END)
        artists = self.app.music_library.get_artists()
        for artist in artists:
            self.artists_az_listbox.insert(tk.END, artist)

    def on_artist_az_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            selected_artist = widget.get(selection[0])
            self.search_entry_var.set(selected_artist) # Put artist name in search bar
            self.perform_search() # Perform search for this artist

    def populate_most_popular_list(self):
        self.most_popular_listbox.delete(0, tk.END)
        all_videos = self.app.music_library.get_all_videos()
        if not all_videos:
            self.most_popular_listbox.insert(tk.END, "(No music in library)")
            return

        import random
        # Display up to 10 random songs as "suggestions"
        num_to_show = min(len(all_videos), 10)
        suggestions = random.sample(all_videos, num_to_show)
        
        for song in suggestions:
            # Store the full path as a hidden part of the item if needed, or lookup later
            # For now, just display. We will need to store the song object or path to go to details.
            # A simple way is to store the path and then retrieve the song object.
            # Let's store the index in all_videos, or the path. Path is better for stability if list changes.
            display_text = f"{song['artist']} - {song['title']}"
            self.most_popular_listbox.insert(tk.END, display_text)
            # Associate data with listbox item (not directly supported by tk.Listbox easily without custom widgets)
            # So, we'll rely on matching the text or re-fetching on selection.
            # A better way for complex data: use a dictionary to map display_text to song_object

    def on_popular_song_double_clicked(self, event):
        widget = event.widget
        selection = widget.curselection()
        if selection:
            selected_display_text = widget.get(selection[0])
            # Now we need to find the song_details matching this text.
            # This is inefficient if lists are very long.
            # A better approach for popular_listbox would be to store song paths or IDs.
            # For now, let's iterate:
            found_song = None
            for song in self.app.music_library.get_all_videos(): # Re-fetch or use a stored list for suggestions
                if f"{song['artist']} - {song['title']}" == selected_display_text:
                    found_song = song
                    break
            
            if found_song:
                self.show_details_view(found_song)
            else:
                self.app.logger.warning(f"Could not find song details for popular list selection: {selected_display_text}")

    # In __init__ or another method, make sure these are called when library changes:
    # self.populate_artists_az_list()
    # self.populate_most_popular_list()
    # For example, in app_controller, after music_library.scan_videos(), call a method in main_ui to refresh these.

    def refresh_sidebar_lists(self): # New method
        self.populate_artists_az_list()
        self.populate_most_popular_list()

    def reset_idle_timer_event(self, event=None):
        # Only reset if the event didn't originate from an Entry widget's text input
        # or if it's a mouse click anywhere. This prevents idle mode during typing.
        if event and isinstance(event.widget, (ttk.Entry, tk.Text)) and event.type == tk.EventType.KeyPress:
            # Could add more specific checks for key types if needed
            pass # Don't reset on every key press in text fields, let typing continue
        else:
            self.reset_idle_timer()

    def reset_idle_timer(self):
        if self.idle_timer_id:
            self.window.after_cancel(self.idle_timer_id)
        
        if self.is_idle:
            self.exit_idle_mode() # If we were idle, interacting should bring us out

        # Only set timer if app is in a state where idle mode is appropriate
        # (e.g., queue empty, not currently playing - app controller can inform UI)
        if self.app.can_go_idle(): # New method in app_controller
             self.idle_timer_id = self.window.after(self.idle_timeout_ms, self.enter_idle_mode)
        else:
            self.idle_timer_id = None # Ensure no timer if not appropriate

    def enter_idle_mode(self):
        if not self.app.can_go_idle(): # Double check
            self.reset_idle_timer()
            return

        self.app.logger.info("Entering idle mode.")
        self.is_idle = True
        # For now, just change the search view slightly.
        # A real idle mode would likely take over the screen.
        self.search_entry_var.set("Touch screen to start searching...")
        self.search_entry.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        # Could hide artist/popular lists or show a different main content
        # e.g., self.search_view_frame.pack_forget(), self.idle_view_frame.pack(...)

    def exit_idle_mode(self):
        self.app.logger.info("Exiting idle mode.")
        self.is_idle = False
        self.search_entry_var.set("") # Clear idle message
        self.search_entry.config(state=tk.NORMAL)
        self.search_button.config(state=tk.NORMAL)
        self.reset_idle_timer() # Restart the countdown

    def periodic_update(self): # Already exists or create it
        # This can be used to check conditions for idle timer if app state changes externally
        # For example, if queue becomes empty AND video stops playing.
        if self.app.can_go_idle() and not self.idle_timer_id and not self.is_idle:
            self.reset_idle_timer() # Re-evaluate if timer should start
        
        self.window.after(5000, self.periodic_update) # Reschedule