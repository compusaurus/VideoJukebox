# core/settings_manager.py
import json
import os
import hashlib # For password hashing

DEFAULT_CONFIG_PATH = "config.json"

class SettingsManager:
    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.settings = self._load_defaults()
        self.load_settings()

    def _load_defaults(self):
        return {
            "music_video_directory": "",
            "log_directory": os.path.join(os.getcwd(), "logs"),
            "splash_directory": os.path.join(os.getcwd(), "assets"),
            "splash_image_file": "default_splash.jpg",
            "buttons_position": "bottom", # "bottom", "top", "left", "right"
            "show_splash_on_startup": True,
            "splash_duration_ms": 3000,
            "show_confirmation_prompts": True,
            "default_credit_cost": 3,
            "admin_password_hash": self.hash_password("admin"), # Default password, change this!
            "blocked_artists": [],
            "blocked_genres": [],
            "blocked_tracks": [],
            "last_screen_positions": {} # To store window positions
        }

    def load_settings(self):
        try:
            if not os.path.exists(self.settings["log_directory"]):
                os.makedirs(self.settings["log_directory"])
            if not os.path.exists(self.settings["splash_directory"]):
                os.makedirs(self.settings["splash_directory"])

            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to ensure all keys exist
                    for key, value in loaded_settings.items():
                        if key in self.settings:
                            self.settings[key] = value
            else:
                self.save_settings() # Save defaults if no file
        except Exception as e:
            print(f"Error loading settings: {e}. Using defaults.")
            self.settings = self._load_defaults() # Revert to full defaults on error

    def save_settings(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value

    def hash_password(self, password):
        if password is None:
            # This case should ideally be caught before calling hash_password
            # for critical operations. Returning a non-matching hash or raising an error.
            # For verify_password, returning a non-matching hash is safest.
            return "cannot_hash_none_value_placeholder_for_non_match" 
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password_attempt):
        return self.hash_password(password_attempt) == self.settings.get("admin_password_hash")

    def set_admin_password(self, new_password):
        self.settings["admin_password_hash"] = self.hash_password(new_password)
        self.save_settings()