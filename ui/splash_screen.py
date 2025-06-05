#ui/splash_screen.py
import tkinter as tk
from PIL import Image, ImageTk # For loading various image formats

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, image_path, duration_ms, callback_on_close):
        super().__init__(parent)
        self.overrideredirect(True) # No window decorations
        self.callback_on_close = callback_on_close
        
        try:
            self.pil_image = Image.open(image_path)
            self.tk_image = ImageTk.PhotoImage(self.pil_image)
        except Exception as e:
            print(f"Error loading splash image '{image_path}': {e}")
            self.destroy()
            self.callback_on_close()
            return

        # Get screen dimensions to center splash
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        img_width = self.pil_image.width
        img_height = self.pil_image.height

        # Calculate position for center
        x = (screen_width // 2) - (img_width // 2)
        y = (screen_height // 2) - (img_height // 2)

        self.geometry(f"{img_width}x{img_height}+{x}+{y}")

        label = tk.Label(self, image=self.tk_image, highlightthickness=0, borderwidth=0)
        label.pack(expand=True, fill=tk.BOTH)

        self.after(duration_ms, self.close_splash)

    def close_splash(self):
        self.destroy()
        if self.callback_on_close:
            self.callback_on_close()