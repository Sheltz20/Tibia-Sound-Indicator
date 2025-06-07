import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageSequence
import pygame
import time
from pynput import keyboard
import os, sys, traceback, json

# Fix for "lost sys.stdin" error
class DummyStream:
    def __init__(self): pass
    def write(self, data): pass
    def read(self, data): return ''
    def flush(self): pass
    def isatty(self): return False

if not hasattr(sys.stdin, 'isatty'):
    sys.stdin = DummyStream()

# Helper function to locate resources in both dev and PyInstaller environments
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ---------------- Helper for JSON Serialization ----------------
def get_serializable_place_info(widget):
    """
    Returns a filtered copy of widget.place_info() with non-serializable values removed.
    """
    info = widget.place_info().copy()
    if "in" in info:
        del info["in"]
    return info

# ================= Global Exception Handler =================
def global_exception_handler(exctype, value, tb):
    error_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_report.txt")
    with open(error_file_path, "a") as f:
        f.write("\n=========== Exception Occurred ===========\n")
        traceback.print_exception(exctype, value, tb, file=f)
        f.write("===========================================\n")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler

# ================= Tooltip Class =================
class CreateToolTip:
    """
    Displays a tooltip when hovering over a widget.
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # milliseconds
        self.wraplength = 180   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self, event=None):
        x = self.widget.winfo_pointerx()
        y = self.widget.winfo_pointery()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y - 30))
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffff", relief='solid', borderwidth=1,
                         wraplength=self.wraplength, font=("Copilot", 10, "bold"))
        label.pack(ipadx=1)

    def hidetip(self):
        if self.tw:
            self.tw.destroy()
        self.tw = None

# ================= TimerPanel Class (GUI Controls) =================
class TimerPanel:
    def __init__(self, parent, side, timer_label_text, sound_default, sound_presets,
                 countdown_ready_text, tooltip_text=None,
                 add_preset=False, preset_options=None, preset_callback=None,
                 sound_label_rely=0.85, set_sound_callback=None):
        self.parent = parent
        self.side = side
        self.initial_positions = {}
        self.hotkey_combo = []  # Initialize hotkey combo list
        self.hotkey_var = tk.StringVar()  # Initialize hotkey variable
        self.timer_var = tk.StringVar()  # Add timer variable

        # Create hotkey entry with proper bindings
        self.hotkey_entry = ttk.Entry(parent, font=("Copilot", 12, "bold"), width=15,
                                    textvariable=self.hotkey_var)
        self.hotkey_entry.place(relx=0.30, rely=0.65, anchor="w")  # Changed relx from 0.23 to 0.30
        self.initial_positions['hotkey_entry'] = {'relx': 0.30, 'rely': 0.65}

        # Timer entry
        self.timer_entry = ttk.Entry(parent, font=("Copilot", 12, "bold"), width=10,
                                   textvariable=self.timer_var)
        self.timer_entry.place(relx=0.30, rely=0.75, anchor="w")  # Changed relx from 0.23 to 0.30
        self.initial_positions['timer_entry'] = {'relx': 0.30, 'rely': 0.75}

        # Bind Tab after both entries are created
        def focus_timer_entry(event):
            self.timer_entry.focus_set()
            return "break"
        self.hotkey_entry.bind("<Tab>", focus_timer_entry)

        # (Optional) Preset dropdown and momentum checkbox.
        if add_preset and preset_options:
            self.preset_var = tk.StringVar(value="Select Spell")
            self.preset_menu = ttk.Combobox(parent, textvariable=self.preset_var,
                                            values=list(preset_options.keys()),
                                            font=("Copilot", 10, "bold"),
                                            width=15)
            # Update to use local method for handling preset selection
            self.preset_menu.bind("<<ComboboxSelected>>", self.handle_preset_selection)
            self.preset_menu.place(relx=0.92, rely=0.05, anchor="ne")
            self.initial_positions['preset_menu'] = {'relx': 0.92, 'rely': 0.05}
            
            self.momentum_var = tk.BooleanVar(value=False)
            self.momentum_checkbox = ttk.Checkbutton(parent, text="Momentum", variable=self.momentum_var,
                                                      style="TCheckbutton")
            self.momentum_checkbox.place(relx=0.92, rely=0.15, anchor="ne")
            self.initial_positions['momentum_checkbox'] = {'relx': 0.92, 'rely': 0.15}
            
            # Store preset options and callback
            self.preset_options = preset_options
            self.preset_callback = preset_callback
        
        # Countdown label.
        self.countdown_label = ttk.Label(parent, text=countdown_ready_text, font=("Copilot", 24, "bold"))
        self.countdown_label.place(relx=0.5, rely=0.55, anchor="center")
        self.initial_positions['countdown_label'] = {'relx': 0.5, 'rely': 0.55}
        
        # Hotkey controls.
        self.hotkey_label = ttk.Label(parent, text="Hotkey:", font=("Copilot", 10, "bold"))
        self.hotkey_label.place(relx=0.15, rely=0.65, anchor="w")  # Changed relx from 0.10 to 0.15
        self.initial_positions['hotkey_label'] = {'relx': 0.15, 'rely': 0.65}
        
        # Timer controls - use simplified text for left and middle panels
        timer_text = "Timer:"  # Simplified text for all panels
            
        self.timer_label = ttk.Label(parent, text=timer_text, font=("Copilot", 10, "bold"))
        self.timer_label.place(relx=0.15, rely=0.75, anchor="w")  # Changed relx from 0.10 to 0.15
        self.initial_positions['timer_label'] = {'relx': 0.15, 'rely': 0.75}
        
        self.sound_label = ttk.Label(parent, text="Sound:", font=("Copilot", 10, "bold"))
        self.sound_label.place(relx=0.15, rely=0.85, anchor="w")  # Changed relx from 0.10 to 0.15
        self.initial_positions['sound_label'] = {'relx': 0.15, 'rely': 0.85}
        
        self.sound_var = tk.StringVar()
        self.sound_var.set("Select sound")
        options = list(sound_presets.keys()) + ["Custom File..."]
        self.sound_menu = ttk.Combobox(parent, textvariable=self.sound_var, values=options,
                                       font=("Copilot", 10, "bold"), width=15)
        self.sound_menu.bind("<<ComboboxSelected>>", lambda event: set_sound_callback(self.sound_var.get()))
        self.sound_menu.place(relx=0.30, rely=0.85, anchor="w")  # Changed relx from 0.23 to 0.30
        self.initial_positions['sound_menu'] = {'relx': 0.30, 'rely': 0.85}

        # Bind key events to process_hotkey method
        self.hotkey_entry.bind("<KeyPress>", self.process_hotkey)
        self.hotkey_entry.bind("<Control-v>", lambda e: "break")   # Prevent paste
        self.hotkey_entry.bind("<Button-1>", lambda e: self.hotkey_entry.focus_set())  # Allow focus on click
        self.hotkey_entry.bind("<FocusIn>", lambda e: self.start_hotkey_capture())
        self.hotkey_entry.bind("<Button-3>", lambda e: "break")    # Prevent right-click paste

    def handle_preset_selection(self, event):
        """Handle preset selection locally within the panel"""
        selection = self.preset_var.get()
        if selection == "Custom":
            self.timer_entry.delete(0, tk.END)
            self.timer_var.set("")
        else:
            timer_value = self.preset_options.get(selection)
            if timer_value is not None:
                self.timer_entry.delete(0, tk.END)
                self.timer_entry.insert(0, str(timer_value))
                self.timer_var.set(str(timer_value))

    def get_widget_positions(self):
        positions = {}
        widgets = {
            f'{self.side}_countdown_label': self.countdown_label,
            f'{self.side}_hotkey_label': self.hotkey_label,
            f'{self.side}_hotkey_entry': self.hotkey_entry,
            f'{self.side}_timer_label': self.timer_label,
            f'{self.side}_timer_entry': self.timer_entry,
            f'{self.side}_sound_label': self.sound_label,
            f'{self.side}_sound_menu': self.sound_menu
        }
        
        if hasattr(self, 'preset_menu'):
            widgets[f'{self.side}_preset_menu'] = self.preset_menu
        if hasattr(self, 'momentum_checkbox'):
            widgets[f'{self.side}_momentum_checkbox'] = self.momentum_checkbox

        print(f"\nGetting positions for {self.side} panel widgets:")
        for name, widget in widgets.items():
            try:
                info = widget.place_info()
                if info:
                    positions[name] = {
                        'relx': float(info.get('relx', 0)),
                        'rely': float(info.get('rely', 0)),
                        'anchor': info.get('anchor', 'nw')
                    }
                    print(f"{name}: relx={positions[name]['relx']}, rely={positions[name]['rely']}")
                    # If position is 0,0 and we have an initial position, use that
                    if positions[name]['relx'] == 0 and positions[name]['rely'] == 0 and name in self.initial_positions:
                        positions[name] = self.initial_positions[name].copy()
                        print(f"Using initial position for {name}: {positions[name]}")
            except Exception as e:
                print(f"Error getting position for {name}: {e}")
                # Use initial position as fallback
                if name in self.initial_positions:
                    positions[name] = self.initial_positions[name].copy()
        return positions

    def set_widget_positions(self, positions):
        print("\nApplying positions to widgets:")
        widgets = {
            'countdown_label': self.countdown_label,
            'hotkey_label': self.hotkey_label,
            'hotkey_entry': self.hotkey_entry,
            'timer_label': self.timer_label,
            'timer_entry': self.timer_entry,
            'sound_label': self.sound_label,
            'sound_menu': self.sound_menu
        }
        
        if hasattr(self, 'preset_menu'):
            widgets['preset_menu'] = self.preset_menu
        if hasattr(self, 'momentum_checkbox'):
            widgets['momentum_checkbox'] = self.momentum_checkbox

        for name, widget in widgets.items():
            # Remove any 'left_' or 'right_' prefix from the position key
            clean_name = name.replace('left_', '').replace('right_', '')
            if clean_name in positions:
                pos = positions[clean_name]
                try:
                    print(f"Setting {name} to relx={pos['relx']}, rely={pos['rely']}")
                    # Force update before placing
                    self.parent.update_idletasks()
                    
                    # Store current position for verification
                    widget.place(
                        relx=float(pos['relx']),
                        rely=float(pos['rely']),
                        anchor=pos.get('anchor', 'nw')
                    )
                    
                    # Force update after placing
                    self.parent.update_idletasks()
                    
                    # Verify position was set correctly
                    current_pos = widget.place_info()
                    print(f"Verified {name} position: relx={current_pos.get('relx')}, rely={current_pos.get('rely')}")
                    
                except Exception as e:
                    print(f"Error setting position for {name}: {e}")
                    # Fall back to initial position if available
                    if clean_name in self.initial_positions:
                        print(f"Falling back to initial position for {name}")
                        widget.place(**self.initial_positions[clean_name])
            else:
                print(f"Warning: No position found for {name}")

        # Final update to ensure all widgets are properly placed
        self.parent.update_idletasks()

    def validate_timer_entry(self, new_value):
        allowed = "0123456789:"
        for char in new_value:
            if char not in allowed:
                return False
        return True

    def start_hotkey_capture(self):
        """Initialize hotkey capture when entry is focused"""
        if self.hotkey_entry['state'] == "normal":
            self.hotkey_combo = []  # Reset combo list
            self.hotkey_var.set("")  # Clear display
            print("Started hotkey capture")

    def process_hotkey(self, event):
        print(f"Processing hotkey event: {event.keysym}")
        if event.keysym == "BackSpace":
            self.hotkey_combo = []
            self.hotkey_var.set("")
            return "break"
        if event.keysym == "Tab":
            # Allow normal tabbing, do not record as hotkey
            return  # Do not return "break" so default focus behavior occurs
        # Map for modifier keys
        modifier_map = {
            "Control_L": "CTRL", "Control_R": "CTRL",
            "Alt_L": "ALT", "Alt_R": "ALT",
            "Shift_L": "SHIFT", "Shift_R": "SHIFT"
        }
        # Map for special keys
        special_key_map = {
            "space": "SPACE",
            "Return": "RETURN",
            "Escape": "ESC",
            "Delete": "DEL",
            "Up": "UP",
            "Down": "DOWN",
            "Left": "LEFT",
            "Right": "RIGHT",
            "grave": "GRAVE",
            "asciitilde": "GRAVE",
            "minus": "-",
            "equal": "=",
            "bracketleft": "[",
            "bracketright": "]",
            "backslash": "\\",
            "semicolon": ";",
            "apostrophe": "'",
            "comma": ",",
            "period": ".",
            "slash": "/",
            "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
            "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
            "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12"
        }

        # Handle modifier keys
        if event.keysym in modifier_map:
            mod = modifier_map[event.keysym]
            if mod not in self.hotkey_combo:
                self.hotkey_combo.append(mod)
        else:
            # Remove any non-modifier keys from the combo
            self.hotkey_combo = [k for k in self.hotkey_combo if k in ["CTRL", "ALT", "SHIFT"]]
            
            # Handle special keys and regular keys
            if event.keysym in special_key_map:
                key_name = special_key_map[event.keysym]
            elif len(event.keysym) == 1:  # Single character keys
                key_name = event.keysym.upper()
            else:  # Other special keys
                key_name = event.keysym.upper()
            
            self.hotkey_combo.append(key_name)

        # Sort modifiers consistently
        mods = [m for m in ["CTRL", "ALT", "SHIFT"] if m in self.hotkey_combo]
        keys = [k for k in self.hotkey_combo if k not in ["CTRL", "ALT", "SHIFT"]]
        
        # Update the display
        combo_string = "+".join(mods + keys)
        print(f"Final hotkey combo: {combo_string}")
        self.hotkey_var.set(combo_string)
        return "break"

# ================= Main Application Class =================
class TibiaTimerApp:
    def __init__(self, root):
        self.root = root
        self.setup_paths()
        self.init_pygame()
        self.init_variables()
        self.setup_gui()
        self.load_user_settings()  # <-- Load settings after GUI setup
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_paths(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.sound_file_left = resource_path("assets/chime.mp3")
        self.sound_file_right = resource_path("assets/Potion.mp3")
        self.image_path_left = resource_path("assets/spells.gif")
        self.image_path_right = resource_path("assets/Buff.gif")
        self.icon_path = resource_path("assets/Wizard1.ico")
        self.top_left_image_path = resource_path("assets/Transparentmage.png")
        self.click_file = resource_path("assets/click.mp3")
        self.user_settings_file = get_settings_path()

    def init_pygame(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(0.5)
            self.click_sound = pygame.mixer.Sound(self.click_file)
        except Exception as e:
            print("Pygame initialization failed:", e)
            self.click_sound = None

    def init_variables(self):
        self.current_hotkey_left = ''
        self.current_hotkey_middle = ''
        self.current_hotkey_right = ''
        self.current_timer_left = 0
        self.current_timer_middle = 0
        self.current_timer_right = 600
        self.is_counting_left = False
        self.is_counting_middle = False
        self.is_counting_right = False
        self.countdown_left_job = None
        self.countdown_middle_job = None
        self.countdown_right_job = None
        self.last_left_hotkey_time = 0
        self.last_middle_hotkey_time = 0
        self.pressed_keys = set()
        self.listener = None
        self.listening_active = False
        self.left_frames = []
        self.middle_frames = []
        self.right_frames = []
        self.preset_options = {"Ice UE": 40, "Ulu's": 22, "Exori Gran": 6, "Custom": None}
        self.sound_presets_left = {
            "Chime": self.sound_file_left,
            "Spell Ready": resource_path("assets/Spell Ready.mp3"),
            "Jingle": resource_path("assets/Jingle.mp3"),
            "UE Ready": resource_path("assets/UEREADY.mp3"),
            "ULU Ready": resource_path("assets/ULUready.mp3"),
            "Use Food Buff": resource_path ("assets/Use Food Buff.mp3")
        }
        self.sound_presets_middle = self.sound_presets_left.copy()  # Use same presets as left panel
        self.sound_presets_right = {
            "Potion": self.sound_file_right,
            "Use Buff": resource_path("assets/Use Buff.mp3"),
            "Snappy": resource_path("assets/Snappy.mp3"),
            "Bullseye Potion": resource_path("assets/bullseyepotion.mp3"),
            "MM Potion Ready": resource_path("assets/MMPotionready.mp3"),
            "Use Food Buff": resource_path ("assets/Use Food Buff.mp3")
        }

        self.current_sound_left = self.sound_file_left
        self.current_sound_middle = self.sound_file_left
        self.current_sound_right = self.sound_file_right
        self.left_finished_at = None
        self.middle_finished_at = None
        self.right_finished_at = None
        self.drag_mode = False

    def play_click_sound(self):
        if self.click_sound:
            self.click_sound.play()

    def setup_gui(self):
        self.root.title("Tibia Timer")
        # Calculate exact window size:
        # Left panel (400) + Divider (10) + Middle panel (400) + Divider (10) + Right panel (400) = 1220px width
        self.root.geometry("1220x400")  # Increased from 810px to fit third panel
        self.root.resizable(False, False)
        try:
            self.root.iconbitmap(self.icon_path)
        except Exception as e:
            print(f"Icon error: {e}")

        # Create and customize styles for 3D buttons
        style = ttk.Style()
        
        # Configure base styles
        style.configure("TCombobox", font=("Copilot", 12, "bold"))
        style.configure("TCheckbutton", font=("Copilot", 12, "bold"))
        style.configure("TEntry", font=("Copilot", 12, "bold"))

        # Get the background color for contrast
        panel_bg = style.lookup("TFrame", "background")
        
        # Define 3D button styles with custom effects
        button_styles = {
            "FutureStart": {
                "main_color": "#00FF00",  # Green
                "dark_shadow": "#008800",  # Darker green
                "light_shadow": "#88FF88"  # Lighter green
            },
            "FutureStop": {
                "main_color": "#FF0000",  # Red
                "dark_shadow": "#880000",  # Darker red
                "light_shadow": "#FF8888"  # Lighter red
            },
            "FutureReset": {
                "main_color": "#FFA500",  # Orange
                "dark_shadow": "#885500",  # Darker orange
                "light_shadow": "#FFD088"  # Lighter orange
            },
            "FutureLock": {
                "main_color": "#00BFFF",  # Blue
                "dark_shadow": "#0088BB",  # Darker blue
                "light_shadow": "#88DDFF"  # Lighter blue
            }
        }

        # Configure each button style with 3D effects
        for style_name, colors in button_styles.items():
            style.configure(
                f"{style_name}.TButton",
                font=("Copilot", 12, "bold"),
                foreground=colors["main_color"],
                background=panel_bg,
                borderwidth=2,
                relief="raised",
                padding=(10, 5)
            )
            
            # Normal state
            style.map(
                f"{style_name}.TButton",
                background=[
                    ("active", colors["light_shadow"]),
                    ("pressed", colors["dark_shadow"])
                ],
                foreground=[
                    ("active", colors["dark_shadow"]),
                    ("pressed", colors["light_shadow"])
                ],
                bordercolor=[
                    ("active", colors["main_color"]),
                    ("pressed", colors["dark_shadow"])
                ],
                relief=[
                    ("active", "ridge"),
                    ("pressed", "sunken")
                ],
                padding=[
                    ("pressed", (10, 5))
                ]
            )

        # Create frames with 3D effect
        frame_style = ttk.Style()
        frame_style.configure("3D.TFrame",
                            borderwidth=2,
                            relief="raised",
                            background=panel_bg)

        # Create left, middle and right panels with 3D effect
        self.left_frame = ttk.Frame(self.root, width=400, height=400, style="3D.TFrame")
        self.left_frame.place(x=0, y=0, width=400, height=400)
        
        self.middle_frame = ttk.Frame(self.root, width=400, height=400, style="3D.TFrame")
        self.middle_frame.place(x=410, y=0, width=400, height=400)
        
        self.right_frame = ttk.Frame(self.root, width=400, height=400, style="3D.TFrame")
        self.right_frame.place(x=820, y=0, width=400, height=400)
        
        # Configure dividers
        style.configure("Divider.TFrame",
                       background="black",
                       borderwidth=0,
                       relief="flat")
        self.left_divider = ttk.Frame(self.root, width=10, height=400, style="Divider.TFrame")
        self.left_divider.place(x=400, y=0, height=400)
        
        self.right_divider = ttk.Frame(self.root, width=10, height=400, style="Divider.TFrame")
        self.right_divider.place(x=810, y=0, height=400)

        # Create buttons with enhanced 3D styling
        self.start_stop_btn = ttk.Button(
            self.right_frame,
            text="Start",
            command=self.toggle_listener,
            style="FutureStart.TButton"
        )
        self.start_stop_btn.place(x=310, y=10, width=80, height=40)  # Positioned at top right
        
        self.reset_btn = ttk.Button(
            self.right_frame,
            text="Reset",
            command=self.reset_all,
            style="FutureReset.TButton"
        )
        self.reset_btn.place(x=310, y=60, width=80, height=40)  # Positioned directly below start button
        
        # Setup images and create panels
        self.setup_images()
        
        # Create TimerPanels
        self.left_panel = TimerPanel(
            parent=self.left_frame,
            side="left",
            timer_label_text="Timer (s):",
            sound_default="Select sound",
            sound_presets=self.sound_presets_left,
            countdown_ready_text="Spell Ready",
            tooltip_text="(mm:ss or ss)",
            add_preset=True,
            preset_options=self.preset_options,
            preset_callback=self.apply_preset_option,
            sound_label_rely=0.85,
            set_sound_callback=self.set_sound_left
        )
        
        self.middle_panel = TimerPanel(
            parent=self.middle_frame,
            side="middle",
            timer_label_text="Timer (s):",
            sound_default="Select sound",
            sound_presets=self.sound_presets_middle,
            countdown_ready_text="Spell Ready",
            tooltip_text="(mm:ss or ss)",
            add_preset=True,
            preset_options=self.preset_options,
            preset_callback=self.apply_preset_option,
            sound_label_rely=0.85,
            set_sound_callback=self.set_sound_middle
        )
        
        self.right_panel = TimerPanel(
            parent=self.right_frame,
            side="right",
            timer_label_text="Timer:",
            sound_default="Select sound",
            sound_presets=self.sound_presets_right,
            countdown_ready_text="Buff Ready",
            tooltip_text="(mm:ss or ss)",
            add_preset=False,
            sound_label_rely=0.85,
            set_sound_callback=self.set_sound_right
        )

        # Volume controls for right frame
        self.volume_var = tk.DoubleVar(value=50)
        self.volume_scale = ttk.Scale(
            self.right_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            command=self.update_volume,
            length=100,
            variable=self.volume_var
        )
        self.volume_scale.place(relx=0.04, rely=0.02, anchor="nw")
        self.vol_label = ttk.Label(self.right_frame, text="50%", font=("Copilot", 12, "bold"))
        self.vol_label.place(relx=0.12, rely=0.065, anchor="nw")

    def setup_images(self):
        """Create image labels for the application"""
        try:
            print("Base path:", os.path.dirname(os.path.abspath(__file__)))
            print("Assets path:", resource_path("assets/spells.gif"))
            print("Assets exists:", os.path.exists(resource_path("assets/spells.gif")))
            
            # Load the top left image (transparent wizard)
            try:
                pil_image = Image.open(self.top_left_image_path)
                # Resize to 94x94 with antialiasing
                pil_image = pil_image.resize((94, 94), Image.Resampling.LANCZOS)
                self.top_left_img = ImageTk.PhotoImage(pil_image)
                # Place in top left corner of the left panel with a small margin
                self.top_left_label = tk.Label(self.left_frame, image=self.top_left_img, bd=0)
                self.top_left_label.place(x=2, y=2)
                print("Loaded top left image successfully")
            except Exception as e:
                print(f"Error loading top left image: {e}")
                self.top_left_label = tk.Label(self.left_frame, bd=0)
                self.top_left_label.place(x=2, y=2)
            
            # Load the left panel GIF (spells)
            try:
                self.left_gif = Image.open(self.image_path_left)
                self.left_frames = []
                for frame in ImageSequence.Iterator(self.left_gif):
                    frame_copy = frame.copy()
                    self.left_frames.append(ImageTk.PhotoImage(frame_copy))
                
                self.left_image_label = tk.Label(self.left_frame, image=self.left_frames[0], bd=0)
                self.left_image_label.place(relx=0.5, rely=0.35, anchor="center")
                self.left_frame_idx = 0
                self.left_after_id = self.root.after(200, self.update_left_gif)
                print("Loaded left GIF successfully")
            except Exception as e:
                print(f"Error loading left GIF: {e}")
                self.left_image_label = tk.Label(self.left_frame, bd=0)
                self.left_image_label.place(relx=0.5, rely=0.35, anchor="center")
            
            # Load the middle panel GIF (same as left for now)
            try:
                self.middle_gif = Image.open(self.image_path_left)  # Reuse left image path
                self.middle_frames = []
                for frame in ImageSequence.Iterator(self.middle_gif):
                    frame_copy = frame.copy()
                    self.middle_frames.append(ImageTk.PhotoImage(frame_copy))
                
                self.middle_image_label = tk.Label(self.middle_frame, image=self.middle_frames[0], bd=0)
                self.middle_image_label.place(relx=0.5, rely=0.35, anchor="center")
                self.middle_frame_idx = 0
                self.middle_after_id = self.root.after(200, self.update_middle_gif)
                print("Loaded middle GIF successfully")
            except Exception as e:
                print(f"Error loading middle GIF: {e}")
                self.middle_image_label = tk.Label(self.middle_frame, bd=0)
                self.middle_image_label.place(relx=0.5, rely=0.35, anchor="center")
            
            # Load the right panel GIF (buff)
            try:
                self.right_gif = Image.open(self.image_path_right)
                self.right_frames = []
                for frame in ImageSequence.Iterator(self.right_gif):
                    frame_copy = frame.copy()
                    self.right_frames.append(ImageTk.PhotoImage(frame_copy))
                
                self.right_image_label = tk.Label(self.right_frame, image=self.right_frames[0], bd=0)
                self.right_image_label.place(relx=0.5, rely=0.35, anchor="center")
                self.right_frame_idx = 0
                self.right_after_id = self.root.after(200, self.update_right_gif)
                print("Loaded right GIF successfully")
            except Exception as e:
                print(f"Error loading right GIF: {e}")
                self.right_image_label = tk.Label(self.right_frame, bd=0)
                self.right_image_label.place(relx=0.5, rely=0.35, anchor="center")
            
            print("Image labels created successfully")
            
        except Exception as e:
            print(f"Error in setup_images: {e}")
            traceback.print_exc()

    def update_left_gif(self):
        """Update the left GIF animation"""
        try:
            if hasattr(self, 'left_frames') and self.left_frames:
                self.left_frame_idx = (self.left_frame_idx + 1) % len(self.left_frames)
                self.left_image_label.configure(image=self.left_frames[self.left_frame_idx])
                self.left_after_id = self.root.after(200, self.update_left_gif)
        except Exception as e:
            print(f"Error updating left GIF: {e}")
            
    def update_middle_gif(self):
        """Update the middle GIF animation"""
        try:
            if hasattr(self, 'middle_frames') and self.middle_frames:
                self.middle_frame_idx = (self.middle_frame_idx + 1) % len(self.middle_frames)
                self.middle_image_label.configure(image=self.middle_frames[self.middle_frame_idx])
                self.middle_after_id = self.root.after(200, self.update_middle_gif)
        except Exception as e:
            print(f"Error updating middle GIF: {e}")
            
    def update_right_gif(self):
        """Update the right GIF animation"""
        try:
            if hasattr(self, 'right_frames') and self.right_frames:
                self.right_frame_idx = (self.right_frame_idx + 1) % len(self.right_frames)
                self.right_image_label.configure(image=self.right_frames[self.right_frame_idx])
                self.right_after_id = self.root.after(200, self.update_right_gif)
        except Exception as e:
            print(f"Error updating right GIF: {e}")

    def toggle_listener(self):
        self.play_click_sound()
        
        try:
            if not self.listening_active:
                # Save the current hotkey values
                self.current_hotkey_left = self.left_panel.hotkey_var.get()
                self.current_hotkey_middle = self.middle_panel.hotkey_var.get()
                self.current_hotkey_right = self.right_panel.hotkey_var.get()
                
                # Save the timer values
                try:
                    left_timer = self.left_panel.timer_entry.get()
                    middle_timer = self.middle_panel.timer_entry.get()
                    right_timer = self.right_panel.timer_entry.get()
                    
                    if left_timer:
                        self.current_timer_left = self.parse_timer(left_timer)
                    if middle_timer:
                        self.current_timer_middle = self.parse_timer(middle_timer)
                    if right_timer:
                        self.current_timer_right = self.parse_timer(right_timer)
                except ValueError as e:
                    messagebox.showerror("Invalid Timer", "Please enter valid timer values.")
                    return
                
                print(f"Starting listener with hotkeys - Left: {self.current_hotkey_left}, Middle: {self.current_hotkey_middle}, Right: {self.current_hotkey_right}")
                print(f"Timer values - Left: {self.current_timer_left}s, Middle: {self.current_timer_middle}s, Right: {self.current_timer_right}s")
                
                # Disable entry fields while listening
                self.left_panel.hotkey_entry.config(state="disabled")
                self.left_panel.timer_entry.config(state="disabled")
                self.middle_panel.hotkey_entry.config(state="disabled")
                self.middle_panel.timer_entry.config(state="disabled")
                self.right_panel.hotkey_entry.config(state="disabled")
                self.right_panel.timer_entry.config(state="disabled")
                
                # Stop any existing listener first
                if self.listener:
                    self.listener.stop()
                    self.listener = None
                
                # Start new listener
                started = self.start_hotkey_listener()
                print(f"Listener started: {started}")
                if self.listener and self.listener.is_alive():
                    print("Listener is alive")
                    self.start_stop_btn.configure(text="Stop", style="FutureStop.TButton")
                    self.listening_active = True
                else:
                    print("Failed to start listener")
            else:
                # Stop listening
                if self.listener:
                    self.listener.stop()
                    self.listener = None
                self.start_stop_btn.configure(text="Start", style="FutureStart.TButton")
                self.cancel_timers()
                self.listening_active = False
                
                # Re-enable entry fields
                self.left_panel.hotkey_entry.config(state="normal")
                self.left_panel.timer_entry.config(state="normal")
                self.middle_panel.hotkey_entry.config(state="normal")
                self.middle_panel.timer_entry.config(state="normal")
                self.right_panel.hotkey_entry.config(state="normal")
                self.right_panel.timer_entry.config(state="normal")
                
        except Exception as e:
            print(f"Error in toggle_listener: {e}")
            traceback.print_exc()

    def reset_all(self):
        self.play_click_sound()
        
        # Stop the listener if it's active
        if self.listening_active:
            if self.listener:
                self.listener.stop()
                self.listener = None
            self.listening_active = False
        
        # Reset the Start/Stop button
        self.start_stop_btn.configure(text="Start", style="FutureStart.TButton")
        
        # Cancel all timers and reset countdown labels
        self.cancel_timers()
        self.left_panel.countdown_label.config(text="Spell Ready")
        self.middle_panel.countdown_label.config(text="Spell Ready")
        self.right_panel.countdown_label.config(text="Buff Ready")
        
        # Clear all timer and hotkey entries
        self.left_panel.timer_entry.delete(0, tk.END)
        self.left_panel.hotkey_entry.delete(0, tk.END)
        self.middle_panel.timer_entry.delete(0, tk.END)
        self.middle_panel.hotkey_entry.delete(0, tk.END)
        self.right_panel.timer_entry.delete(0, tk.END)
        self.right_panel.hotkey_entry.delete(0, tk.END)
        
        # Reset all sound selections
        self.left_panel.sound_var.set("Select sound")
        self.middle_panel.sound_var.set("Select sound")
        self.right_panel.sound_var.set("Select sound")
        
        # Reset preset selections and momentum checkboxes
        if hasattr(self.left_panel, "preset_var"):
            self.left_panel.preset_var.set("Select Spell")
        if hasattr(self.left_panel, "momentum_var"):
            self.left_panel.momentum_var.set(False)
        if hasattr(self.middle_panel, "preset_var"):
            self.middle_panel.preset_var.set("Select Spell")
        if hasattr(self.middle_panel, "momentum_var"):
            self.middle_panel.momentum_var.set(False)
            
        # Reset all timer and hotkey variables
        self.current_hotkey_left = ''
        self.current_hotkey_middle = ''
        self.current_hotkey_right = ''
        self.current_timer_left = 0
        self.current_timer_middle = 0
        self.current_timer_right = 600
        self.left_finished_at = None
        self.middle_finished_at = None
        self.right_finished_at = None
        
        # Reset timer variables in panels
        self.left_panel.timer_var.set("")
        self.middle_panel.timer_var.set("")
        self.right_panel.timer_var.set("")
        
        # Reset hotkey variables in panels
        self.left_panel.hotkey_var.set("")
        self.middle_panel.hotkey_var.set("")
        self.right_panel.hotkey_var.set("")
        
        # Re-enable all entry fields
        self.left_panel.hotkey_entry.config(state="normal")
        self.left_panel.timer_entry.config(state="normal")
        self.middle_panel.hotkey_entry.config(state="normal")
        self.middle_panel.timer_entry.config(state="normal")
        self.right_panel.hotkey_entry.config(state="normal")
        self.right_panel.timer_entry.config(state="normal")
        
        # Re-enable all sound menus
        self.left_panel.sound_menu.config(state="normal")
        self.middle_panel.sound_menu.config(state="normal")
        self.right_panel.sound_menu.config(state="normal")

    def update_volume(self, value):
        """Update the volume level for pygame sounds"""
        try:
            vol = float(value) / 100.0
            pygame.mixer.music.set_volume(vol)
            self.vol_label.config(text=f"{int(float(value))}%")
        except Exception as e:
            print(f"Error in update_volume: {e}")
            traceback.print_exc()

    def cancel_timers(self):
        """Cancel all ongoing countdown timers"""
        try:
            if hasattr(self, 'is_counting_left') and self.is_counting_left and hasattr(self, 'countdown_left_job') and self.countdown_left_job is not None:
                self.root.after_cancel(self.countdown_left_job)
                self.left_panel.countdown_label.config(text="Spell Ready")
                self.is_counting_left = False
                
            if hasattr(self, 'is_counting_right') and self.is_counting_right and hasattr(self, 'countdown_right_job') and self.countdown_right_job is not None:
                self.root.after_cancel(self.countdown_right_job)
                self.right_panel.countdown_label.config(text="Buff Ready")
                self.is_counting_right = False
                
            if hasattr(self, 'is_counting_middle') and self.is_counting_middle and hasattr(self, 'countdown_middle_job') and self.countdown_middle_job is not None:
                self.root.after_cancel(self.countdown_middle_job)
                self.middle_panel.countdown_label.config(text="Spell Ready")
                self.is_counting_middle = False
        except Exception as e:
            print(f"Error in cancel_timers: {e}")
            traceback.print_exc()
    
    def start_hotkey_listener(self):
        """Start the keyboard listener for hotkeys"""
        try:
            # Initialize pressed_keys if it doesn't exist
            if not hasattr(self, 'pressed_keys'):
                self.pressed_keys = set()
            
            # Create and start new listener
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()
            
            # Wait a short time to ensure the listener starts
            time.sleep(0.1)
            
            if not self.listener.is_alive():
                print("Listener failed to start")
                return False
            
            print("Hotkey listener started successfully")
            return True
        except Exception as e:
            print(f"Error starting hotkey listener: {e}")
            traceback.print_exc()
            return False

    def set_sound_left(self, selection):
        """Set the sound for the left panel"""
        try:
            if selection == "Select sound":
                self.current_sound_left = self.sound_file_left
            elif selection == "Custom File...":
                file_path = filedialog.askopenfilename(title="Select an MP3 File", filetypes=[("MP3 Files", "*.mp3")])
                if file_path:
                    if not file_path.lower().endswith(".mp3"):
                        messagebox.showerror("Invalid File", "Please select a valid MP3 file.")
                        self.left_panel.sound_var.set("Select sound")
                        self.current_sound_left = self.sound_file_left
                    else:
                        file_size = os.path.getsize(file_path)
                        if file_size > 102400:
                            messagebox.showerror("File Too Large", "File must be no more than 100kb.")
                            self.left_panel.sound_var.set("Select sound")
                            self.current_sound_left = self.sound_file_left
                        else:
                            self.current_sound_left = file_path
                            self.left_panel.sound_var.set("Custom Sound")
                else:
                    self.left_panel.sound_var.set("Select sound")
                    self.current_sound_left = self.sound_file_left
            else:
                self.current_sound_left = self.sound_presets_left.get(selection, "")
        except Exception as e:
            print(f"Error in set_sound_left: {e}")
            traceback.print_exc()

    def set_sound_middle(self, selection):
        """Set the sound for the middle panel"""
        try:
            if selection == "Select sound":
                self.current_sound_middle = self.sound_file_left
            elif selection == "Custom File...":
                file_path = filedialog.askopenfilename(title="Select an MP3 File", filetypes=[("MP3 Files", "*.mp3")])
                if file_path:
                    if not file_path.lower().endswith(".mp3"):
                        messagebox.showerror("Invalid File", "Please select a valid MP3 file.")
                        self.middle_panel.sound_var.set("Select sound")
                        self.current_sound_middle = self.sound_file_left
                    else:
                        file_size = os.path.getsize(file_path)
                        if file_size > 102400:
                            messagebox.showerror("File Too Large", "File must be no more than 100kb.")
                            self.middle_panel.sound_var.set("Select sound")
                            self.current_sound_middle = self.sound_file_left
                        else:
                            self.current_sound_middle = file_path
                            self.middle_panel.sound_var.set("Custom Sound")
                else:
                    self.middle_panel.sound_var.set("Select sound")
                    self.current_sound_middle = self.sound_file_left
            else:
                self.current_sound_middle = self.sound_presets_middle.get(selection, "")
        except Exception as e:
            print(f"Error in set_sound_middle: {e}")
            traceback.print_exc()

    def set_sound_right(self, selection):
        """Set the sound for the right panel"""
        try:
            if selection == "Select sound":
                self.current_sound_right = self.sound_file_right
            elif selection == "Custom File...":
                file_path = filedialog.askopenfilename(title="Select an MP3 File", filetypes=[("MP3 Files", "*.mp3")])
                if file_path:
                    if not file_path.lower().endswith(".mp3"):
                        messagebox.showerror("Invalid File", "Please select a valid MP3 file.")
                        self.right_panel.sound_var.set("Select sound")
                        self.current_sound_right = self.sound_file_right
                    else:
                        file_size = os.path.getsize(file_path)
                        if file_size > 102400:
                            messagebox.showerror("File Too Large", "File must be no more than 100kb.")
                            self.right_panel.sound_var.set("Select sound")
                            self.current_sound_right = self.sound_file_right
                        else:
                            self.current_sound_right = file_path
                            self.right_panel.sound_var.set("Custom Sound")
                else:
                    self.right_panel.sound_var.set("Select sound")
                    self.current_sound_right = self.sound_file_right
            else:
                self.current_sound_right = self.sound_presets_right.get(selection, "")
        except Exception as e:
            print(f"Error in set_sound_right: {e}")
            traceback.print_exc()

    def apply_preset_option(self, selection):
        """Apply a preset option for timers"""
        try:
            if selection == "Custom":
                self.left_panel.timer_entry.delete(0, tk.END)
                self.current_timer_left = 0
            else:
                timer_value = self.preset_options.get(selection)
                if timer_value is not None:
                    self.left_panel.timer_entry.delete(0, tk.END)
                    self.left_panel.timer_entry.insert(0, str(timer_value))
                    self.current_timer_left = timer_value
        except Exception as e:
            print(f"Error in apply_preset_option: {e}")
            traceback.print_exc()

    def parse_timer(self, timer_str):
        """Parse a timer string into seconds"""
        try:
            if ":" in timer_str:
                parts = timer_str.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes * 60 + seconds
                else:
                    raise ValueError("Time must be in mm:ss format")
            else:
                return int(timer_str)
        except Exception as e:
            print(f"Error parsing timer: {e}")
            traceback.print_exc()
            return 0

    def on_press(self, key):
        """Handle key press events from the pynput listener"""
        try:
            # Initialize the set if it doesn't exist
            if not hasattr(self, 'pressed_keys'):
                self.pressed_keys = set()
            
            # Add the key to pressed_keys set
            self.pressed_keys.add(key)
            
            # Build the current combination
            combo_parts = []
            
            # Check for modifiers first
            if any(k in self.pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
                combo_parts.append("CTRL")
            if any(k in self.pressed_keys for k in (keyboard.Key.alt_l, keyboard.Key.alt_r)):
                combo_parts.append("ALT")
            if any(k in self.pressed_keys for k in (keyboard.Key.shift_l, keyboard.Key.shift_r)):
                combo_parts.append("SHIFT")

            # Get the main key
            if isinstance(key, keyboard.KeyCode):
                # Handle special virtual key codes
                vk_map = {
                    192: "GRAVE",    # Backtick/grave key (US layout)
                    223: "GRAVE",    # Backtick/grave key (alternate code)
                    0xC0: "GRAVE",   # Backtick/grave key (hex code)
                    189: "-",        # Minus
                    187: "=",        # Equals
                    219: "[",        # Left bracket
                    221: "]",        # Right bracket
                    220: "\\",       # Backslash
                    186: ";",        # Semicolon
                    222: "'",        # Quote
                    188: ",",        # Comma
                    190: ".",        # Period
                    191: "/",        # Forward slash
                    32: "SPACE",     # Space
                    # Add number keys
                    48: "0", 49: "1", 50: "2", 51: "3", 52: "4",
                    53: "5", 54: "6", 55: "7", 56: "8", 57: "9",
                    # Add numpad keys
                    96: "0", 97: "1", 98: "2", 99: "3", 100: "4",
                    101: "5", 102: "6", 103: "7", 104: "8", 105: "9",
                    # Add alphabet keys
                    65: "A", 66: "B", 67: "C", 68: "D", 69: "E",
                    70: "F", 71: "G", 72: "H", 73: "I", 74: "J",
                    75: "K", 76: "L", 77: "M", 78: "N", 79: "O",
                    80: "P", 81: "Q", 82: "R", 83: "S", 84: "T",
                    85: "U", 86: "V", 87: "W", 88: "X", 89: "Y",
                    90: "Z"
                }

                # First try to match by virtual key code
                if hasattr(key, 'vk') and key.vk is not None:
                    if key.vk in vk_map:
                        key_name = vk_map[key.vk]
                        combo_parts.append(key_name)
                    elif 96 <= key.vk <= 105:  # Numpad numbers
                        key_name = str(key.vk - 96)
                        combo_parts.append(key_name)
                # Then try by character
                elif hasattr(key, 'char') and key.char:
                    if key.char in ('`', '~'):
                        combo_parts.append("GRAVE")
                    elif key.char.isdigit():
                        combo_parts.append(key.char)
                    else:
                        # For standard letter keys, convert to uppercase and append
                        key_name = key.char.upper()
                        combo_parts.append(key_name)
                        
            elif isinstance(key, keyboard.Key):
                # Skip if it's just a modifier key
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                          keyboard.Key.alt_l, keyboard.Key.alt_r,
                          keyboard.Key.shift_l, keyboard.Key.shift_r):
                    return
                
                # Map special keys
                special_keys = {
                    keyboard.Key.space: "SPACE",
                    keyboard.Key.enter: "RETURN",
                    keyboard.Key.esc: "ESCAPE",
                    keyboard.Key.delete: "DELETE",
                    keyboard.Key.up: "UP",
                    keyboard.Key.down: "DOWN",
                    keyboard.Key.left: "LEFT",
                    keyboard.Key.right: "RIGHT",
                }
                
                if key in special_keys:
                    key_name = special_keys[key]
                    combo_parts.append(key_name)
                else:
                    key_name = key.name.upper()
                    combo_parts.append(key_name)

            # Build the final combo string
            if combo_parts:
                combo = "+".join(combo_parts)
                
                # Debug prints for troubleshooting key listening
                print(f"Pressed keys combo: {combo}")
                print(f"Current hotkeys - Left: {self.current_hotkey_left}, Middle: {self.current_hotkey_middle}, Right: {self.current_hotkey_right}")
                
                # Normalize combo string to uppercase without spaces for comparison
                normalized_combo = combo.replace(" ", "").upper()
                normalized_left = self.current_hotkey_left.replace(" ", "").upper()
                normalized_middle = self.current_hotkey_middle.replace(" ", "").upper()
                normalized_right = self.current_hotkey_right.replace(" ", "").upper()
                
                print(f"Normalized combo: {normalized_combo}")
                print(f"Normalized hotkeys - Left: {normalized_left}, Middle: {normalized_middle}, Right: {normalized_right}")
                
                # Check against saved hotkeys
                if normalized_combo == normalized_left:
                    print("Matched left hotkey, starting countdown left")
                    self.start_countdown_left()
                elif normalized_combo == normalized_middle:
                    print("Matched middle hotkey, starting countdown middle")
                    self.start_countdown_middle()
                elif normalized_combo == normalized_right:
                    print("Matched right hotkey, starting countdown right")
                    self.start_countdown_right()

        except Exception as e:
            print(f"Error in on_press: {e}")
            traceback.print_exc()

    def on_release(self, key):
        """Handle key release events from the pynput listener"""
        try:
            if key in self.pressed_keys:
                self.pressed_keys.remove(key)
        except Exception as e:
            print(f"Error in on_release: {e}")
            traceback.print_exc()
            
    def start_countdown_left(self):
        """Start the countdown for the left panel"""
        try:
            if hasattr(self, "left_panel") and hasattr(self.left_panel, "momentum_var") and self.left_panel.momentum_var.get():
                current_time = time.time()
                if current_time - self.last_left_hotkey_time < 2:
                    return
                if self.is_counting_left and self.countdown_left_job is not None:
                    self.root.after_cancel(self.countdown_left_job)
                self.countdown_left(self.current_timer_left)
                self.is_counting_left = True
                self.last_left_hotkey_time = current_time
                return
                
            if self.is_counting_left:
                return
                
            current_time = time.time()
            if current_time - self.last_left_hotkey_time > 3:
                self.countdown_left(self.current_timer_left)
                self.is_counting_left = True
                self.last_left_hotkey_time = current_time
        except Exception as e:
            print(f"Error in start_countdown_left: {e}")
            traceback.print_exc()
            
    def start_countdown_middle(self):
        """Start the countdown for the middle panel"""
        try:
            if hasattr(self, "middle_panel") and hasattr(self.middle_panel, "momentum_var") and self.middle_panel.momentum_var.get():
                current_time = time.time()
                if current_time - self.last_middle_hotkey_time < 2:
                    return
                if self.is_counting_middle and self.countdown_middle_job is not None:
                    self.root.after_cancel(self.countdown_middle_job)
                self.countdown_middle(self.current_timer_middle)
                self.is_counting_middle = True
                self.last_middle_hotkey_time = current_time
                return
                
            if self.is_counting_middle:
                return
                
            current_time = time.time()
            if current_time - self.last_middle_hotkey_time > 3:
                self.countdown_middle(self.current_timer_middle)
                self.is_counting_middle = True
                self.last_middle_hotkey_time = current_time
        except Exception as e:
            print(f"Error in start_countdown_middle: {e}")
            traceback.print_exc()
            
    def start_countdown_right(self):
        """Start the countdown for the right panel"""
        try:
            if self.is_counting_right and self.countdown_right_job is not None:
                self.root.after_cancel(self.countdown_right_job)
            self.countdown_right(self.current_timer_right)
            self.is_counting_right = True
        except Exception as e:
            print(f"Error in start_countdown_right: {e}")
            traceback.print_exc()
            
    def countdown_left(self, time_left):
        """Handle the countdown for the left panel"""
        try:
            if time_left > 0:
                color = "green" if time_left <= 5 else "black"
                self.left_panel.countdown_label.config(text=f"Ready in: {time_left}s", foreground=color)
                self.countdown_left_job = self.root.after(1000, self.countdown_left, time_left - 1)
            else:
                self.left_panel.countdown_label.config(text="UE Ready")
                self.left_finished_at = time.time()
                if self.current_sound_left:
                    pygame.mixer.music.load(self.current_sound_left)
                    pygame.mixer.music.play()
                self.is_counting_left = False
        except Exception as e:
            print(f"Error in countdown_left: {e}")
            traceback.print_exc()
            
    def countdown_middle(self, time_left):
        """Handle the countdown for the middle panel"""
        try:
            if time_left > 0:
                color = "green" if time_left <= 5 else "black"
                self.middle_panel.countdown_label.config(text=f"Ready in: {time_left}s", foreground=color)
                self.countdown_middle_job = self.root.after(1000, self.countdown_middle, time_left - 1)
            else:
                self.middle_panel.countdown_label.config(text="UE Ready")
                self.middle_finished_at = time.time()
                if self.current_sound_middle:
                    pygame.mixer.music.load(self.current_sound_middle)
                    pygame.mixer.music.play()
                self.is_counting_middle = False
        except Exception as e:
            print(f"Error in countdown_middle: {e}")
            traceback.print_exc()
            
    def countdown_right(self, time_left):
        """Handle the countdown for the right panel"""
        try:
            if time_left > 0:
                minutes = time_left // 60
                seconds = time_left % 60
                color = "green" if time_left <= 5 else "black"
                self.right_panel.countdown_label.config(text=f"Ready in: {minutes:02d}:{seconds:02d}", foreground=color)
                self.countdown_right_job = self.root.after(1000, self.countdown_right, time_left - 1)
            else:
                self.right_panel.countdown_label.config(text="Potion Ready")
                self.right_finished_at = time.time()
                if self.current_sound_right:
                    if (self.left_finished_at is not None and (self.right_finished_at - self.left_finished_at) < 2):
                        self.root.after(1000, self.play_right_sound)
                    else:
                        self.play_right_sound()
                self.is_counting_right = False
        except Exception as e:
            print(f"Error in countdown_right: {e}")
            traceback.print_exc()
            
    def play_right_sound(self):
        """Play the right panel sound"""
        try:
            if self.current_sound_right:
                pygame.mixer.music.load(self.current_sound_right)
                pygame.mixer.music.play()
        except Exception as e:
            print(f"Error in play_right_sound: {e}")
            traceback.print_exc()

    def on_closing(self):
        """Handles cleanup when the application is closing"""
        try:
            # Stop any active timers and listeners
            if hasattr(self, 'listening_active') and self.listening_active:
                if hasattr(self, 'listener') and self.listener:
                    self.listener.stop()
                    self.listener = None
                self.listening_active = False
            self.cancel_timers()

            # Cancel GIF animations
            for attr in ["left_after_id", "middle_after_id", "right_after_id"]:
                if hasattr(self, attr):
                    self.root.after_cancel(getattr(self, attr))

            # Collect current settings
            self.collect_user_settings()

            # Save user settings
            self.save_user_settings()

        except Exception as e:
            print(f"Error in on_closing: {e}")
            traceback.print_exc()
        finally:
            self.root.destroy()

    def collect_user_settings(self):
        # Hotkeys
        self.hotkey_settings = {
            "left": self.left_panel.hotkey_var.get(),
            "middle": self.middle_panel.hotkey_var.get(),
            "right": self.right_panel.hotkey_var.get()
        }
        # Timers
        self.timer_settings = {
            "left": self.left_panel.timer_var.get(),
            "middle": self.middle_panel.timer_var.get(),
            "right": self.right_panel.timer_var.get()
        }
        # Sound selections
        self.sound_settings = {
            "left": self.left_panel.sound_var.get(),
            "middle": self.middle_panel.sound_var.get(),
            "right": self.right_panel.sound_var.get()
        }

    def save_user_settings(self):
        """Save user input settings (hotkeys, times, sound selection)"""
        settings = {
            "hotkeys": self.hotkey_settings,  
            "times": self.timer_settings,
            "sound_selection": self.sound_settings
        }

        with open(self.user_settings_file, "w") as f:  # ✅ Now `self.user_settings_file` works
            json.dump(settings, f, indent=4)

        print("User settings saved successfully.")

    def load_user_settings(self):
        """Load user input settings (hotkeys, times, sound selection) and apply to GUI widgets"""
        try:
            if not os.path.exists(self.user_settings_file):
                return
            with open(self.user_settings_file, "r") as f:
                settings = json.load(f)
            # Restore hotkeys
            hotkeys = settings.get("hotkeys", {})
            self.left_panel.hotkey_var.set(hotkeys.get("left", ""))
            self.middle_panel.hotkey_var.set(hotkeys.get("middle", ""))
            self.right_panel.hotkey_var.set(hotkeys.get("right", ""))
            # Restore timers
            timers = settings.get("times", {})
            self.left_panel.timer_var.set(timers.get("left", ""))
            self.middle_panel.timer_var.set(timers.get("middle", ""))
            self.right_panel.timer_var.set(timers.get("right", ""))
            # Also update the entry widgets
            self.left_panel.timer_entry.delete(0, tk.END)
            self.left_panel.timer_entry.insert(0, timers.get("left", ""))
            self.middle_panel.timer_entry.delete(0, tk.END)
            self.middle_panel.timer_entry.insert(0, timers.get("middle", ""))
            self.right_panel.timer_entry.delete(0, tk.END)
            self.right_panel.timer_entry.insert(0, timers.get("right", ""))
            # Restore sound selections
            sounds = settings.get("sound_selection", {})
            left_sound = sounds.get("left", "Select sound")
            middle_sound = sounds.get("middle", "Select sound")
            right_sound = sounds.get("right", "Select sound")
            self.left_panel.sound_var.set(left_sound)
            self.middle_panel.sound_var.set(middle_sound)
            self.right_panel.sound_var.set(right_sound)
            # Update current_sound_* variables by calling set_sound_* methods
            self.set_sound_left(left_sound)
            self.set_sound_middle(middle_sound)
            self.set_sound_right(right_sound)
        except Exception as e:
            print(f"Error loading user settings: {e}")
            traceback.print_exc()

def get_settings_path():
    appdata = os.getenv('APPDATA')  # e.g., C:\\Users\\Ben Shelton\\AppData\\Roaming
    folder = os.path.join(appdata, "TibiaTimer")
    if not os.path.exists(folder):
        os.makedirs(folder)
    return os.path.join(folder, "Tibia Timer Saved settings.json")

# Add the main function
if __name__ == "__main__":
    try:
        root = ttk.Window(themename="darkly")
        root.geometry("1220x400")
        def tk_exception_handler(exc, val, tb):
            global_exception_handler(type(exc), exc, tb)
        root.report_callback_exception = tk_exception_handler
        app = TibiaTimerApp(root)
        root.mainloop()
    except Exception as e:
        global_exception_handler(type(e), e, e.__traceback__)
        input("An error occurred. Press Enter to exit...")
