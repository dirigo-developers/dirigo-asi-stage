import customtkinter as ctk
from tkinter import messagebox
from time import sleep
from MS2000 import MS2000
from StageControl import StageControl

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class StageGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ASI Stage Control")

        # Initialize stage
        try:
            self.stage = MS2000()
            print("Stage initialized successfully")
        except Exception as e:
            messagebox.showerror("Stage Error", f"Failed to initialize stage:\n{e}")
            self.destroy()
            return

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Stage control widget
        self.stage_control = StageControl(
            self.main_frame,
            move_stage_callback=self.stage_move_handler,
            zero_callback=self.stage_zero,
            home_callback=self.stage_home,
            get_stage_coords=self.get_stage_coords
        )
        self.stage_control.pack(fill="both", expand=True, padx=10, pady=10)

    def get_stage_coords(self):
        """Get current stage position in tenths of microns"""
        try:
            return self.stage.position(x=True, y=True, z=True)
        except Exception as e:
            print(f"Error getting stage position: {e}")
            return (0, 0, 0)

    def stage_move_handler(self, **kwargs):
        """Handle stage movement requests"""
        while not self.stage.status():
            sleep(0.05)
        
        try:
            mode = kwargs.get("mode")
            if mode == "coordinate":
                x = kwargs.get('x')
                y = kwargs.get('y')
                z = kwargs.get('z')
                # Convert mm to tenths of microns, only pass axes that have values
                x = float(x * 10000) if x is not None else None
                y = float(y * 10000) if y is not None else None
                z = float(z * 10000) if z is not None else None
                self.stage.move(x=x, y=y, z=z, relative=False)
            elif mode == "z":
                z = kwargs.get('z', 0)
                self.stage.move(z=z, relative=True)
            elif mode == "xy":
                x = kwargs.get('x')
                y = kwargs.get('y')
                # x and y are already in tenths of microns from XYControl
                self.stage.move(x=x, y=y, z=None, relative=True)
        except Exception as e:
            messagebox.showerror("Stage Move Error", f"Failed to move stage:\n{e}")
            print("Error:", e)

    def stage_zero(self):
        """Zero the stage coordinates"""
        try:
            self.stage.zero()
        except Exception as e:
            print(f"Failed to zero stage: {e}")

    def stage_home(self):
        """Move stage to (0, 0, 0)"""
        try:
            while not self.stage.status():
                sleep(0.05)
            self.stage.home()
        except Exception as e:
            print(f"Failed to move stage home: {e}")

    def on_closing(self):
        """Handle window close event"""
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to quit?"):
            try:
                self.stage.close()
            except:
                pass
            self.quit()
            self.destroy()


if __name__ == "__main__":
    app = StageGUI()
    app.mainloop()
