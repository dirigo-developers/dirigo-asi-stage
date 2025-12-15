import customtkinter as ctk
from tkinter import messagebox

class XYControl(ctk.CTkFrame):
    def __init__(self, master, move_xy_func, step_size_var=None, **kwargs):
        super().__init__(master, **kwargs)
        self.move_xy = move_xy_func
        self.step_size_var = step_size_var if step_size_var else ctk.StringVar(value="25µm")
        
        self.step_map = {"1µm": 1, "5µm": 5, "10µm": 10, "25µm": 25, "50µm": 50, "100µm": 100}

        # Arrow buttons in a 3x3 grid layout with "XY" label in center
        #     ▲
        #  ◄  XY  ►
        #     ▼
        self.up_btn = ctk.CTkButton(self, text="▲", command=self.move_up, width=50)
        self.up_btn.grid(row=0, column=1, padx=5, pady=5)

        self.left_btn = ctk.CTkButton(self, text="◄", command=self.move_left, width=50)
        self.left_btn.grid(row=1, column=0, padx=5, pady=5)

        self.xy_label = ctk.CTkLabel(self, text="XY", font=ctk.CTkFont(size=14, weight="bold"))
        self.xy_label.grid(row=1, column=1, padx=5, pady=5)

        self.right_btn = ctk.CTkButton(self, text="►", command=self.move_right, width=50)
        self.right_btn.grid(row=1, column=2, padx=5, pady=5)

        self.down_btn = ctk.CTkButton(self, text="▼", command=self.move_down, width=50)
        self.down_btn.grid(row=2, column=1, padx=5, pady=5)

    def move_left(self):
        step = float(self.step_map[self.step_size_var.get()])
        self.move_xy(x=-round(10 * step, 3))

    def move_right(self):
        step = float(self.step_map[self.step_size_var.get()])
        self.move_xy(x=round(10 * step, 3))

    def move_up(self):
        step = float(self.step_map[self.step_size_var.get()])
        self.move_xy(y=round(10 * step, 3))

    def move_down(self):
        step = float(self.step_map[self.step_size_var.get()])
        self.move_xy(y=-round(10 * step, 3))


class ZControl(ctk.CTkFrame):
    def __init__(self, master, move_z_func, step_size_var=None, **kwargs):
        super().__init__(master, **kwargs)
        self.move_z = move_z_func
        self.step_size_var = step_size_var if step_size_var else ctk.StringVar(value="25µm")
        
        self.step_map = {"1µm": 1, "5µm": 5, "10µm": 10, "25µm": 25, "50µm": 50, "100µm": 100}

        # Arrow buttons in a 3x1 grid layout with "Z" label in center
        #     ▲
        #     Z
        #     ▼
        self.up_btn = ctk.CTkButton(self, text="▲", command=self.move_up, width=50)
        self.up_btn.grid(row=0, column=0, padx=5, pady=5)

        self.z_label = ctk.CTkLabel(self, text="Z", font=ctk.CTkFont(size=14, weight="bold"))
        self.z_label.grid(row=1, column=0, padx=5, pady=5)

        self.down_btn = ctk.CTkButton(self, text="▼", command=self.move_down, width=50)
        self.down_btn.grid(row=2, column=0, padx=5, pady=5)

    def move_up(self):
        step = float(self.step_map[self.step_size_var.get()])
        self.move_z(round(-10 * step, 3))

    def move_down(self):
        step = float(self.step_map[self.step_size_var.get()])
        self.move_z(round(10 * step, 3))


class StageControl(ctk.CTkFrame):
    def __init__(self, master, move_stage_callback, zero_callback, home_callback, get_stage_coords, **kwargs):
        super().__init__(master, **kwargs)

        self.move_stage_callback = move_stage_callback
        self.zero_callback = zero_callback
        self.home_callback = home_callback
        self.get_stage_coords = get_stage_coords

        # Row 1: Step size selections
        step_size_frame = ctk.CTkFrame(self)
        step_size_frame.pack(pady=5, fill="x", expand=True)

        xy_label = ctk.CTkLabel(step_size_frame, text="XY Step Size:")
        xy_label.pack(side=ctk.LEFT, padx=5)

        self.xy_step_size = ctk.StringVar(value="25µm")
        self.xy_dropdown = ctk.CTkOptionMenu(step_size_frame, values=["1µm", "5µm", "10µm", "25µm", "50µm", "100µm"],
                                             variable=self.xy_step_size,
                                             command=self._on_xy_step_change)
        self.xy_dropdown.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)

        z_label = ctk.CTkLabel(step_size_frame, text="Z Step Size:")
        z_label.pack(side=ctk.LEFT, padx=5)

        self.z_step_size = ctk.StringVar(value="25µm")
        self.z_dropdown = ctk.CTkOptionMenu(step_size_frame, values=["1µm", "5µm", "10µm", "25µm", "50µm", "100µm"],
                                           variable=self.z_step_size,
                                           command=self._on_z_step_change)
        self.z_dropdown.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)

        # Row 2: XY and Z movement controls
        movement_frame = ctk.CTkFrame(self)
        movement_frame.pack(pady=5, fill="x", expand=True)

        # XY control section
        xy_control_frame = ctk.CTkFrame(movement_frame)
        xy_control_frame.pack(side=ctk.LEFT, padx=10, fill="both", expand=True)

        step_map = {"1µm": 1, "5µm": 5, "10µm": 10, "25µm": 25, "50µm": 50, "100µm": 100}
        
        def move_xy(x=None, y=None):
            if x is not None:
                self.move_stage_callback(mode="xy", x=x, y=None, z=None)
            if y is not None:
                self.move_stage_callback(mode="xy", x=None, y=y, z=None)

        self.xy_control = XYControl(xy_control_frame, move_xy, step_size_var=self.xy_step_size)
        self.xy_control.pack()

        # Z control section
        z_control_frame = ctk.CTkFrame(movement_frame)
        z_control_frame.pack(side=ctk.LEFT, padx=10, fill="both", expand=True)

        def move_z(z):
            self.move_stage_callback(mode="z", x=None, y=None, z=z)

        self.z_control = ZControl(z_control_frame, move_z, step_size_var=self.z_step_size)
        self.z_control.pack()

        # Row 3: Coordinate entry
        coord_frame = ctk.CTkFrame(self)
        coord_frame.pack(pady=5, fill="x", expand=True)

        ctk.CTkLabel(coord_frame, text="Move to Position (mm):").pack(side=ctk.LEFT, padx=5)
        
        self.stage_x_entry = ctk.CTkEntry(coord_frame, placeholder_text="X (mm)")
        self.stage_x_entry.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)
        
        self.stage_y_entry = ctk.CTkEntry(coord_frame, placeholder_text="Y (mm)")
        self.stage_y_entry.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)
        
        self.stage_z_entry = ctk.CTkEntry(coord_frame, placeholder_text="Z (mm)")
        self.stage_z_entry.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)

        # Row 4: Command buttons
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(pady=5, fill="x", expand=True)

        self.move_btn = ctk.CTkButton(buttons_frame, text="Move", command=self.move_stage)
        self.move_btn.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)

        self.zero_btn = ctk.CTkButton(buttons_frame, text="Zero", command=self.zero_callback)
        self.zero_btn.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)

        self.home_btn = ctk.CTkButton(buttons_frame, text="Home", command=self.home_callback)
        self.home_btn.pack(side=ctk.LEFT, padx=5, fill="x", expand=True)

        # Coordinate label
        self.coord_label = ctk.CTkLabel(self, text="Stage: (x, y, z) = (---, ---, ---)")
        self.coord_label.pack(pady=5)

        self._update_coords()

    def _on_xy_step_change(self, value):
        """Update XY control step size when dropdown changes"""
        pass  # Step size is already synced via shared variable

    def _on_z_step_change(self, value):
        """Update Z control step size when dropdown changes"""
        pass  # Step size is already synced via shared variable

    def move_stage(self):
        try:
            x_str = self.stage_x_entry.get().strip()
            y_str = self.stage_y_entry.get().strip()
            z_str = self.stage_z_entry.get().strip()
            
            x = float(x_str) if x_str else None
            y = float(y_str) if y_str else None
            z = float(z_str) if z_str else None
            
            self.move_stage_callback(mode="coordinate", x=x, y=y, z=z)
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid numbers")

    def _update_coords(self):
        try:
            x, y, z = self.get_stage_coords()
            self.coord_label.configure(text=f"Current stage position: (x, y, z) mm =\n({x/10000:.4f}, {y/10000:.4f}, {z/10000:.4f})")
        except Exception as e:
            self.coord_label.configure(text="Stage: Error")
            print("Failed to get stage coords:", e)   
        finally:
            self.after(100, self._update_coords)  # Refresh every 100 ms
