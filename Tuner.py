import os
import configparser
import tkinter as tk
from tkinter import messagebox

try:
    from lib.gui_ltacc import LiveTuningAccess_win
except ImportError as e:
    messagebox.showerror(
        master=None,
        title="Module Import Error!",
        message=f"Could not import LiveTuningAccess_win. Ensure 'lib/gui_ltacc.py' exists and is in the correct path.\nError: {e}"
    )
    raise e

def run_live_tuning_access_standalone():
    root = tk.Tk()
    root.withdraw()

    PREFS_FILE = 'prefs.cfg'
    prefs = configparser.ConfigParser()

    try:
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, 'r') as f:
                prefs.read_file(f)
        else:
            messagebox.showwarning(
                master=root,
                title="Preferences Warning",
                message=f"'{PREFS_FILE}' not found. Live-Tuning Access will start with default settings."
            )
    except Exception as e:
        messagebox.showerror(
            master=root,
            title="Error Reading Preferences",
            message=f"An error occurred while reading '{PREFS_FILE}': {e}"
        )

    tuner_script_dir = os.path.dirname(os.path.abspath(__file__))

    LiveTuningAccess_win(prefs, root, tuner_script_dir)

    root.mainloop()

    try:
        with open(PREFS_FILE, 'w') as f:
            prefs.write(f)
    except Exception as e:
        messagebox.showwarning(
            master=None,
            title="Preferences Save Error",
            message=f"Could not save preferences to '{PREFS_FILE}': {e}"
        )

if __name__ == "__main__":
    run_live_tuning_access_standalone()