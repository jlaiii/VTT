import sys, os, subprocess, datetime, importlib.metadata, platform, struct, traceback

# ================================================================
# CRASH LOG — catches ALL errors to crash_log.txt next to the script
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRASH_LOG_PATH = os.path.join(BASE_DIR, "crash_log.txt")
_CRASH_LOG_FH = open(CRASH_LOG_PATH, "w", encoding="utf-8")
_CRASH_LOG_FH.write(f"=== VTT Crash Log [{datetime.datetime.now()}]\n")
sys.stderr = _CRASH_LOG_FH
def _log_crash(msg):
    try:
        _CRASH_LOG_FH.write(f"{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} {msg}\n")
        _CRASH_LOG_FH.flush()
    except:
        pass
_log_crash("Boot: crash logging active")

if sys.platform == "win32" and not sys.executable.lower().endswith("pythonw.exe"):
    _pythonw = sys.executable[:sys.executable.lower().rfind("python.exe")] + "pythonw.exe"
    if os.path.isfile(_pythonw):
        _log_crash(f"Re-launching via pythonw: {_pythonw}")
        subprocess.Popen(
            [_pythonw, __file__],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        sys.exit()
    else:
        _log_crash("pythonw.exe not found, freeing console")
        try:
            import ctypes
            ctypes.windll.kernel32.FreeConsole()
        except:
            pass

try:
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    _log_crash("ShowWindow failed (expected if no console)")

# =========================
# STARTUP LOGGING HELPERS
# =========================
_startup_logs = []

def _startup_log(msg, level="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _startup_logs.append((ts, level, msg))
    _log_crash(f"[{level}] {msg}")

# =========================
# DEPENDENCY CHECK & AUTO-INSTALL
# =========================
REQUIREMENTS = {
    "customtkinter":      "customtkinter",
    "speech_recognition": "SpeechRecognition",
    "pyautogui":          "PyAutoGUI",
    "sounddevice":        "sounddevice",
    "numpy":              "numpy",
    "scipy":              "scipy",
    "keyboard":           "keyboard",
}

def _ensure_packages():
    _startup_log("Scanning dependencies...")
    missing = []
    for disp, pkg in REQUIREMENTS.items():
        try:
            ver = importlib.metadata.version(pkg)
            _startup_log(f"{disp} v{ver} OK", "OK")
        except importlib.metadata.PackageNotFoundError:
            _startup_log(f"{disp} MISSING", "WARN")
            missing.append(pkg)
        except Exception as e:
            _startup_log(f"{disp} check failed: {e}", "ERROR")
            missing.append(pkg)

    if not missing:
        _startup_log("All dependencies OK", "OK")
        return True

    _startup_log(f"Installing {len(missing)} package(s): {', '.join(missing)}")
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + missing,
            capture_output=True, text=True, creationflags=flags
        )
        if result.returncode == 0:
            _startup_log("Installation complete", "OK")
            for disp, pkg in REQUIREMENTS.items():
                if pkg in missing:
                    try:
                        ver = importlib.metadata.version(pkg)
                        _startup_log(f"{disp} v{ver} installed OK", "OK")
                    except Exception:
                        _startup_log(f"{disp} verify FAILED", "ERROR")
            return True
        else:
            err = result.stderr.strip() or "Unknown pip error"
            _startup_log(f"pip failed: {err}", "ERROR")
            return False
    except Exception as e:
        _startup_log(f"Install error: {e}", "ERROR")
        return False

_ensure_packages()

# =========================
# CONFIG & PERSISTENCE
# =========================
CONFIG_FILE = os.path.join(BASE_DIR, "vtt_settings.json")

_startup_log(f"VTT Startup — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
_startup_log(f"OS: {platform.platform()}")
_startup_log(f"Python: {sys.version.split()[0]} ({struct.calcsize('P') * 8}-bit)")
_startup_log(f"Executable: {sys.executable}")
_startup_log(f"Work Dir: {BASE_DIR}")

# Audio device scan
try:
    import sounddevice as sd
    mics = sd.query_devices()
    input_devs = [d for d in mics if d.get("max_input_channels", 0) > 0]
    _startup_log(f"Audio devices: {len(input_devs)} input(s) found")
    if input_devs:
        _startup_log(f"Default mic: {input_devs[0]['name']}")
    else:
        _startup_log("No audio input devices found!", "WARN")
except Exception as e:
    _startup_log(f"Audio device scan FAILED: {e}", "ERROR")

# Now safe to import all third-party + stdlib packages
import threading, time, json, traceback, io, queue, random, tkinter as tk, webbrowser
from tkinter import messagebox
import customtkinter as ctk
import speech_recognition as sr
import pyautogui
import numpy as np
from scipy.io.wavfile import write
import difflib
import keyboard

DEFAULT_SETTINGS = {
    "auto_enter": False,
    "enter_delay": "3s",
    "delay": "0.01s",
    "sensitivity": "Medium",
    "idle_stop": "Never",
    "last_x": 100,
    "last_y": 100,
    "always_on_top": False,
    "toggle_hotkey": "",
}

def load_settings():
    s = DEFAULT_SETTINGS.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: s.update(json.load(f))
        except: pass
    return s

def save_settings(data):
    try:
        with open(CONFIG_FILE, "w") as f: json.dump(data, f)
    except: pass

# =========================
# MAIN APP
# =========================
class VTT(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VTT")
        self.config = load_settings()
        self.geometry(f"280x380+{self.config['last_x']}+{self.config['last_y']}")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.running = False
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()

        self.recognizer.pause_threshold = 2.0
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.8

        self.last_sent_words = []
        self.last_speech_time = time.time()
        self.enter_pending = False
        self.settings_window = None
        self.log_widget = None
        self.log_window = None

        self.setup_ui()
        self.attributes("-topmost", self.config.get("always_on_top", False))
        self.update_threshold()
        self.bind("<Configure>", self.save_pos)
        self.bind_all("<Key>", self._on_key, add="+")
        self._load_hotkey()

    def setup_ui(self):
        ctk.CTkLabel(self, text="VTT", font=("Impact", 45)).pack(pady=(15, 0))
        ctk.CTkLabel(self, text="Powered by Google", font=("Arial", 10), text_color="grey").pack(pady=(0, 10))

        self.btn_run = ctk.CTkButton(self, text="START VOICE ENGINE", height=45, fg_color="#27AE60", font=("Arial", 15, "bold"), command=self.toggle_vtt)
        self.btn_run.pack(pady=10, padx=35, fill="x")

        self.auto_enter_var = tk.BooleanVar(value=self.config.get("auto_enter", False))
        ctk.CTkCheckBox(self, text="Enable Auto-Enter", variable=self.auto_enter_var, command=self.sync_auto).pack(pady=5)

        ctk.CTkButton(self, text="⚙ SETTINGS", width=120, command=self.open_settings).pack(pady=10)

        self.lbl_status = ctk.CTkLabel(self, text="● IDLE", text_color="grey")
        self.lbl_status.pack()

        ctk.CTkLabel(self, text="by jlaiii", font=("Arial", 11), text_color="grey").pack(side="bottom", pady=(0, 0))
        self.lbl_github = ctk.CTkLabel(self, text="GitHub", font=("Arial", 12, "underline"), text_color="#3498DB", cursor="hand2")
        self.lbl_github.pack(side="bottom", pady=(0, 8))
        self.lbl_github.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/jlaiii/VTT"))

    def on_closing(self):
        self.running = False
        self._clear_hotkey()
        self.destroy()
        os._exit(0)

    def update_threshold(self):
        sens_map = {"High": 1400, "Medium": 550, "Low": 180}
        self.recognizer.energy_threshold = sens_map.get(self.config["sensitivity"], 550)

    def sync_auto(self):
        self.config["auto_enter"] = self.auto_enter_var.get()
        save_settings(self.config)

    def center_on_parent(self, win, w, h):
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        self.center_on_parent(self.settings_window, 340, 520)
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.focus_force()

    def add_log(self, category, message, level="INFO"):
        if self.log_widget and self.log_widget.winfo_exists():
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            color_map = {"ERROR": "#E74C3C", "WARN": "#F39C12", "OK": "#2ECC71", "INFO": None}
            tag = category.upper()
            clean_msg = f"[{ts}] [{level}] {tag}: {message}\n"
            self.log_widget.insert("end", clean_msg)
            if color_map.get(level):
                start = self.log_widget.index(f"end-{len(clean_msg)}c")
                end = self.log_widget.index("end-1c")
                self.log_widget.tag_add(level, start, end)
                self.log_widget.tag_config(level, foreground=color_map[level])
            self.log_widget.see("end")

    def flush_startup_logs(self):
        for ts, level, msg in _startup_logs:
            self.add_log("Startup", msg, level)
        _startup_logs.clear()

    def save_pos(self, event):
        if not self.running:
            self.config["last_x"], self.config["last_y"] = self.winfo_x(), self.winfo_y()
            save_settings(self.config)

    def _load_hotkey(self):
        hk = self.config.get("toggle_hotkey", "")
        if hk:
            try:
                keyboard.add_hotkey(hk, lambda: self.after(0, self.toggle_vtt))
            except Exception:
                pass

    def _clear_hotkey(self):
        try:
            keyboard.unhook_all()
        except Exception:
            pass

    def set_hotkey(self, keys):
        self._clear_hotkey()
        self.config["toggle_hotkey"] = keys
        save_settings(self.config)
        if keys:
            try:
                keyboard.add_hotkey(keys, lambda: self.after(0, self.toggle_vtt))
                self.add_log("System", f"Hotkey set: {keys}")
            except Exception as e:
                self.add_log("System", f"Hotkey failed: {e}", "ERROR")

    def _on_key(self, event):
        pass

    def set_always_on_top(self, enabled):
        self.attributes("-topmost", enabled)
        self.config["always_on_top"] = enabled
        save_settings(self.config)

    def toggle_vtt(self):
        if not self.running:
            self.running = True
            self.btn_run.configure(text="STOP VOICE ENGINE", fg_color="#C0392B")
            self.lbl_status.configure(text="● ACTIVE", text_color="#2ecc71")
            self.last_speech_time = time.time()
            self.add_log("System", "Engine Online")
            
            threading.Thread(target=self.audio_capture, daemon=True).start()
            threading.Thread(target=self.processor, daemon=True).start()
            threading.Thread(target=self.enter_logic, daemon=True).start()
            threading.Thread(target=self.idle_monitor, daemon=True).start()
        else:
            self.stop_engine()

    def stop_engine(self):
        self.running = False
        self.btn_run.configure(text="START VOICE ENGINE", fg_color="#27AE60")
        self.lbl_status.configure(text="● IDLE", text_color="grey")
        self.add_log("System", "Engine Offline")

    def idle_monitor(self):
        while self.running:
            idle_val = self.config.get("idle_stop", "Never")
            if idle_val != "Never":
                seconds = int(idle_val.replace('s', ''))
                if (time.time() - self.last_speech_time) > seconds:
                    self.add_log("Status", "Auto-Stop Triggered")
                    self.after(0, self.stop_engine)
                    break
            time.sleep(1)

    def audio_capture(self):
        try:
            fs = 16000
            with sd.InputStream(samplerate=fs, channels=1, dtype='int16') as stream:
                while self.running:
                    data, _ = stream.read(1024)
                    self.audio_queue.put(data)
        except:
            self.add_log("Audio", "Capture stream failed", "ERROR")
            self.running = False

    def enter_logic(self):
        while self.running:
            if self.config.get("auto_enter") and self.enter_pending:
                map_delay = {"3s": 3, "5s": 5, "8s": 8, "30s": 30, "1m": 60}
                limit = map_delay.get(self.config["enter_delay"], 3)
                if (time.time() - self.last_speech_time) >= limit:
                    pyautogui.press('enter')
                    self.add_log("Action", "Auto-Enter Triggered")
                    self.enter_pending = False
                    self.last_sent_words = [] 
            time.sleep(0.1)

    def processor(self):
        fs = 16000
        buffer = np.zeros((0, 1), dtype='int16')
        while self.running:
            if not self.audio_queue.empty():
                buffer = np.append(buffer, self.audio_queue.get(), axis=0)
                # INCREASED WINDOW FOR CONTEXT (1.8s)
                if len(buffer) >= (fs * 1.8):
                    try:
                        byte_io = io.BytesIO(); write(byte_io, fs, buffer); byte_io.seek(0)
                        with sr.AudioFile(byte_io) as source:
                            audio = self.recognizer.record(source)
                            raw_text = self.recognizer.recognize_google(audio).lower()
                            if raw_text:
                                self.add_log("Heard", f'"{raw_text}"')
                                current_words = raw_text.split()
                                # Deduplication with slightly higher cutoff for accuracy
                                filtered_words = [w for w in current_words if not difflib.get_close_matches(w, self.last_sent_words[-3:], n=1, cutoff=0.88)]
                                
                                if filtered_words:
                                    final_str = " ".join(filtered_words)
                                    pyautogui.write(final_str + " ", interval=float(self.config["delay"].replace('s','')))
                                    self.last_sent_words.extend(filtered_words)
                                    self.last_sent_words = self.last_sent_words[-12:] # Larger memory
                                    self.last_speech_time = time.time()
                                    self.enter_pending = True
                        
                        # KEEP 0.6s OVERLAP FOR CONTINUITY
                        buffer = buffer[-int(fs * 0.6):]
                    except Exception as ex:
                        self.add_log("Speech", f"Recognition error: {ex}", "WARN")
                        buffer = buffer[-int(fs * 0.2):]
            else: time.sleep(0.05)

# =========================
# WINDOWS
# =========================
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.parent = parent
        self.title("Settings")

        ctk.CTkLabel(self, text="Typing Speed:").pack(pady=(15,0))
        self.speed_drop = ctk.CTkComboBox(self, values=["0.0s", "0.01s", "0.05s", "0.1s"])
        self.speed_drop.pack(); self.speed_drop.set(parent.config["delay"])

        ctk.CTkLabel(self, text="Mic Sensitivity:").pack(pady=(10,0))
        self.sens_drop = ctk.CTkComboBox(self, values=["High", "Medium", "Low"])
        self.sens_drop.pack(); self.sens_drop.set(parent.config["sensitivity"])

        ctk.CTkLabel(self, text="Auto-Enter Delay:").pack(pady=(10,0))
        self.delay_drop = ctk.CTkComboBox(self, values=["3s", "5s", "8s", "30s", "1m"])
        self.delay_drop.pack(); self.delay_drop.set(parent.config["enter_delay"])

        ctk.CTkLabel(self, text="Idle Auto-Stop:").pack(pady=(10,0))
        self.idle_drop = ctk.CTkComboBox(self, values=["10s", "30s", "60s", "Never"])
        self.idle_drop.pack(); self.idle_drop.set(parent.config.get("idle_stop", "Never"))

        self.always_top_var = tk.BooleanVar(value=parent.config.get("always_on_top", False))
        self.always_top_cb = ctk.CTkCheckBox(self, text="Always on Top", variable=self.always_top_var, command=self._toggle_always_top)
        self.always_top_cb.pack(pady=(15, 5))

        ctk.CTkLabel(self, text="Toggle Hotkey:").pack(pady=(10, 0))
        hotkey_frame = ctk.CTkFrame(self, fg_color="transparent")
        hotkey_frame.pack(pady=5)
        self.hotkey_entry = ctk.CTkEntry(hotkey_frame, width=100, placeholder_text="e.g. ctrl+shift+v")
        self.hotkey_entry.pack(side="left", padx=(0, 5))
        self.hotkey_entry.insert(0, parent.config.get("toggle_hotkey", ""))
        self.hotkey_entry.bind("<Key>", lambda e: "break")
        self.hotkey_entry.bind("<KeyRelease>", self._capture_hotkey)
        self._recording_hotkey = False
        ctk.CTkButton(hotkey_frame, text="RECORD", width=60, command=self._start_hotkey_record).pack(side="left")

        ctk.CTkButton(self, text="LOGS", command=self.open_logs).pack(pady=15)
        ctk.CTkButton(self, text="SAVE", command=self.apply, fg_color="#27AE60", height=40).pack(pady=10)

    def _toggle_always_top(self):
        self.parent.set_always_on_top(self.always_top_var.get())

    def _start_hotkey_record(self):
        self._recording_hotkey = True
        self.hotkey_entry.delete(0, "end")
        self.hotkey_entry.insert(0, "Press keys...")

    def _capture_hotkey(self, event):
        if not self._recording_hotkey:
            return
        keys = []
        if event.state & 0x4:
            keys.append("ctrl")
        if event.state & 0x1:
            keys.append("shift")
        if event.state & 0x20000:
            keys.append("alt")
        name = event.keysym.lower()
        if name not in ("control_l", "control_r", "shift_l", "shift_r", "alt_l", "alt_r"):
            keys.append(name)
        if keys:
            combo = "+".join(keys)
            self.hotkey_entry.delete(0, "end")
            self.hotkey_entry.insert(0, combo)
            self._recording_hotkey = False

    def open_logs(self):
        if self.parent.log_window is None or not self.parent.log_window.winfo_exists():
            self.parent.log_window = DebugWindow(self, self.parent)
        self.parent.center_on_parent(self.parent.log_window, 450, 350)
        self.parent.log_window.deiconify()
        self.parent.log_window.lift()
        self.parent.log_window.focus_force()

    def apply(self):
        self.parent.config.update({
            "delay": self.speed_drop.get(),
            "enter_delay": self.delay_drop.get(),
            "sensitivity": self.sens_drop.get(),
            "idle_stop": self.idle_drop.get()
        })
        save_settings(self.parent.config)
        self.parent.update_threshold()
        self.destroy()

class DebugWindow(ctk.CTkToplevel):
    def __init__(self, settings_parent, main_parent):
        super().__init__(settings_parent)
        self.transient(settings_parent)
        self.title("System Logs")
        self.geometry("450x350")
        
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        ctk.CTkButton(self, text="CLEAR", height=28, width=80, fg_color="#34495E", 
                      command=lambda: self.log_box.delete("1.0", "end")).pack(pady=5)
        main_parent.log_widget = self.log_box
        main_parent.flush_startup_logs()

if __name__ == "__main__":
    try:
        _log_crash("Boot: entering mainloop")
        VTT().mainloop()
    except Exception:
        tb = traceback.format_exc()
        _log_crash(f"FATAL:\n{tb}")
        _CRASH_LOG_FH.close()
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("VTT Fatal Error", f"Check crash_log.txt next to VTT.pyw\n\n{tb.splitlines()[-1]}")
        except:
            pass
        sys.exit(1)
    finally:
        try: _CRASH_LOG_FH.close()
        except: pass