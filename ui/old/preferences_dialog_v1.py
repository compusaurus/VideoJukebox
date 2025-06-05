# ui/preferences_dialog.py
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class PreferencesDialog(tk.Toplevel):
    def __init__(self, parent, settings_manager, app_controller=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Preferences")
        self.settings_manager = settings_manager
        self.app_controller = app_controller
        self.grab_set() # Modal

        self.vars = {}

        self.create_widgets()
        self.load_settings_to_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        # Center window (optional)
        # self.geometry(f"+{parent.winfo_rootx()+50}+{parent.winfo_rooty()+50}")

    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        # --- Directory Settings ---
        dir_frame = ttk.LabelFrame(frame, text="Directories & Files", padding="10")
        dir_frame.pack(fill=tk.X, pady=5)

        row = 0
        self._add_path_entry(dir_frame, row, "Music Video Directory:", "music_video_directory")
        row += 1
        self._add_path_entry(dir_frame, row, "Log Directory:", "log_directory")
        row += 1
        self._add_path_entry(dir_frame, row, "Splash Directory:", "splash_directory")
        row += 1
        self._add_file_entry(dir_frame, row, "Splash Image File:", "splash_image_file",
                             [("Image files", "*.jpg *.jpeg *.png *.gif")])

        # --- Splash Screen Settings ---
        splash_frame = ttk.LabelFrame(frame, text="Splash Screen", padding="10")
        splash_frame.pack(fill=tk.X, pady=5)

        self.vars["show_splash_on_startup"] = tk.BooleanVar()
        ttk.Checkbutton(splash_frame, text="Show splash screen on startup",
                        variable=self.vars["show_splash_on_startup"]).pack(anchor=tk.W)

        splash_duration_frame = ttk.Frame(splash_frame)
        splash_duration_frame.pack(fill=tk.X, pady=2)
        ttk.Label(splash_duration_frame, text="Splash Duration (ms):").pack(side=tk.LEFT)
        self.vars["splash_duration_ms"] = tk.IntVar()
        ttk.Entry(splash_duration_frame, textvariable=self.vars["splash_duration_ms"], width=10).pack(side=tk.LEFT, padx=5)

        # --- UI Settings ---
        ui_frame = ttk.LabelFrame(frame, text="User Interface", padding="10")
        ui_frame.pack(fill=tk.X, pady=5)

        buttons_pos_frame = ttk.Frame(ui_frame)
        buttons_pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(buttons_pos_frame, text="Buttons Position:").pack(side=tk.LEFT)
        self.vars["buttons_position"] = tk.StringVar()
        ttk.Combobox(buttons_pos_frame, textvariable=self.vars["buttons_position"],
                     values=["bottom", "top", "left", "right"], state="readonly").pack(side=tk.LEFT, padx=5)

        self.vars["show_confirmation_prompts"] = tk.BooleanVar()
        ttk.Checkbutton(ui_frame, text="Show confirmation prompts",
                        variable=self.vars["show_confirmation_prompts"]).pack(anchor=tk.W)


        # --- Credits Settings ---
        credits_frame = ttk.LabelFrame(frame, text="Credits", padding="10")
        credits_frame.pack(fill=tk.X, pady=5)
        
        credit_cost_frame = ttk.Frame(credits_frame)
        credit_cost_frame.pack(fill=tk.X, pady=2)
        ttk.Label(credit_cost_frame, text="Default Credit Cost per Song:").pack(side=tk.LEFT)
        self.vars["default_credit_cost"] = tk.IntVar()
        ttk.Entry(credit_cost_frame, textvariable=self.vars["default_credit_cost"], width=5).pack(side=tk.LEFT, padx=5)

        # --- Music Control (Placeholder - expand later) ---
        # music_control_frame = ttk.LabelFrame(frame, text="Music Controls", padding="10")
        # music_control_frame.pack(fill=tk.X, pady=5)
        # ttk.Label(music_control_frame, text="Artist/Genre/Track blocking (TODO)").pack()


        # --- Buttons ---
        button_frame = ttk.Frame(frame, padding="5")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)

    def _add_path_entry(self, parent_frame, row_num, label_text, var_key):
        sub_frame = ttk.Frame(parent_frame)
        sub_frame.pack(fill=tk.X, pady=2) # Use pack instead of grid for sub_frame

        ttk.Label(sub_frame, text=label_text, width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.vars[var_key] = tk.StringVar()
        entry = ttk.Entry(sub_frame, textvariable=self.vars[var_key])
        entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        button = ttk.Button(sub_frame, text="Browse",
                            command=lambda k=var_key: self._browse_directory(k))
        button.pack(side=tk.LEFT)

    def _add_file_entry(self, parent_frame, row_num, label_text, var_key, filetypes):
        sub_frame = ttk.Frame(parent_frame)
        sub_frame.pack(fill=tk.X, pady=2)

        ttk.Label(sub_frame, text=label_text, width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.vars[var_key] = tk.StringVar()
        entry = ttk.Entry(sub_frame, textvariable=self.vars[var_key])
        entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        button = ttk.Button(sub_frame, text="Browse",
                            command=lambda k=var_key, ft=filetypes: self._browse_file(k, ft))
        button.pack(side=tk.LEFT)


    def _browse_directory(self, var_key):
        directory = filedialog.askdirectory(initialdir=self.vars[var_key].get() or os.getcwd())
        if directory:
            self.vars[var_key].set(directory)

    def _browse_file(self, var_key, filetypes):
        initial_dir = os.path.dirname(self.vars[var_key].get() or self.settings_manager.get(os.path.dirname(var_key)))
        if not initial_dir: # If splash_image_file is just a name, use splash_directory
             initial_dir = self.settings_manager.get("splash_directory")
        
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir or os.getcwd(),
            filetypes=filetypes
        )
        if filepath:
            # Store only filename if it's within the splash directory
            splash_dir = self.settings_manager.get("splash_directory")
            if splash_dir and os.path.commonpath([filepath, splash_dir]) == os.path.abspath(splash_dir):
                 self.vars[var_key].set(os.path.basename(filepath))
            else: # Store full path if it's outside
                 self.vars[var_key].set(filepath)


    def load_settings_to_ui(self):
        for key, var in self.vars.items():
            value = self.settings_manager.get(key)
            if value is not None:
                var.set(value)

    def _on_save(self):
        old_music_dir = self.settings_manager.get("music_video_directory")
        new_music_dir_from_ui = self.vars["music_video_directory"].get()

        for key, var in self.vars.items():
            self.settings_manager.set(key, var.get())
        self.settings_manager.save_settings()
        
        # Access the main app controller via parent (assuming parent is the root window of app)
        # A more robust way is to pass the app_controller directly to PreferencesDialog
        # For now, let's assume self.master.master is the app controller if self.master is the root window
        # This is a bit fragile. It's better if PreferencesDialog gets app_controller instance.
        
        # Let's modify PreferencesDialog to accept app_controller
        # So, in main.py when creating PreferencesDialog:
        # PreferencesDialog(self.root, self.settings_manager, self) # Pass 'self' (app_controller)
        # And in PreferencesDialog.__init__:
        # def __init__(self, parent, settings_manager, app_controller):
        #     # ...
        #     self.app_controller = app_controller

        # Assuming self.app_controller is now available:
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.logger.info("Preferences saved.")
            if old_music_dir != new_music_dir_from_ui and new_music_dir_from_ui:
                self.app_controller.logger.info(f"Music video directory changed from '{old_music_dir}' to '{new_music_dir_from_ui}'.")
                if messagebox.askyesno("Apply Changes", "Music video directory has changed. Re-scan library now?", parent=self):
                    self.app_controller.logger.info("User requested library re-scan after preferences change.")
                    if hasattr(self.app_controller, 'music_library') and self.app_controller.music_library:
                        self.app_controller.music_library.scan_videos()
                        if hasattr(self.app_controller, 'main_ui') and self.app_controller.main_ui:
                            self.app_controller.main_ui.refresh_sidebar_lists()
                            self.app_controller.main_ui.perform_search() # Clear/update search results
                        messagebox.showinfo("Library Scan", "Music library re-scan complete.", parent=self)
                    else:
                        messagebox.showwarning("Scan Error", "Could not initiate library scan. Music library component not ready.", parent=self)
            messagebox.showinfo("Preferences", "Settings saved!", parent=self) # Show this after potential scan
        else:
            # Fallback if app_controller not passed (less ideal)
            messagebox.showinfo("Preferences", "Settings saved! Restart or re-scan manually if music directory changed.", parent=self)

        self.destroy()

    def _on_cancel(self):
        self.destroy()