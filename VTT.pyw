import sys, os, subprocess, datetime, importlib.metadata, platform, struct, traceback

# ================================================================
# SESSION LOG — appends ALL events to logs.txt next to the script
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_PATH = os.path.join(BASE_DIR, "logs.txt")

# Open in append mode so history is preserved across launches
_LOG_FH = open(LOGS_PATH, "a", encoding="utf-8")
_LOG_FH.write(f"\n{'='*60}\n")
_LOG_FH.write(f"=== VTT Session [{datetime.datetime.now()}]\n")
_LOG_FH.write(f"{'='*60}\n")
_log_lock = __import__('threading').Lock()  # thread-safe writes

# Redirect stderr to the log file
sys.stderr = _LOG_FH

def _write_log(msg):
    """Thread-safe write to the log file."""
    try:
        with _log_lock:
            _LOG_FH.write(f"{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} {msg}\n")
            _LOG_FH.flush()
    except:
        pass

_write_log("Boot: session logging active")

if sys.platform == "win32" and not sys.executable.lower().endswith("pythonw.exe"):
    _pythonw = sys.executable[:sys.executable.lower().rfind("python.exe")] + "pythonw.exe"
    if os.path.isfile(_pythonw):
        _write_log(f"Re-launching via pythonw: {_pythonw}")
        subprocess.Popen(
            [_pythonw, __file__],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        sys.exit()
    else:
        _write_log("pythonw.exe not found, freeing console")
        try:
            import ctypes
            ctypes.windll.kernel32.FreeConsole()
        except:
            pass

try:
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    _write_log("ShowWindow failed (expected if no console)")

# =========================
# STARTUP LOGGING HELPERS
# =========================
_startup_logs = []

def _startup_log(msg, level="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _startup_logs.append((ts, level, msg))
    _write_log(f"[STARTUP] [{level}] {msg}")

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

OPTIONAL_PACKAGES = {
    "faster_whisper": "faster-whisper",
}
WHISPER_AVAILABLE = False

def _pip_install(packages):
    """Install pip packages and return (success, output_text)."""
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + packages,
        capture_output=True, text=True, creationflags=flags
    )
    return result.returncode == 0, (result.stderr.strip() or result.stdout.strip() or "OK")

def _ensure_packages():
    _startup_log("Scanning required dependencies...")
    missing = []
    for disp, pkg in REQUIREMENTS.items():
        try:
            ver = importlib.metadata.version(pkg)
            _startup_log(f"  {disp} v{ver} ✓", "OK")
        except importlib.metadata.PackageNotFoundError:
            _startup_log(f"  {disp} ✗ MISSING", "WARN")
            missing.append(pkg)
        except Exception as e:
            _startup_log(f"  {disp} ✗ check failed: {e}", "ERROR")
            missing.append(pkg)

    if not missing:
        _startup_log("All required dependencies OK ✓", "OK")
        return True

    _startup_log(f"Installing {len(missing)} required package(s): {', '.join(missing)}")
    ok, output = _pip_install(missing)
    if ok:
        _startup_log("Required packages installed ✓", "OK")
        for disp, pkg in REQUIREMENTS.items():
            if pkg in missing:
                try:
                    ver = importlib.metadata.version(pkg)
                    _startup_log(f"  {disp} v{ver} now available ✓", "OK")
                except Exception:
                    _startup_log(f"  {disp} verify FAILED ✗", "ERROR")
        return True
    else:
        _startup_log(f"pip install FAILED: {output}", "ERROR")
        return False

def _install_optional_packages():
    global WHISPER_AVAILABLE
    _startup_log("Scanning optional packages...")
    for disp, pkg in OPTIONAL_PACKAGES.items():
        try:
            ver = importlib.metadata.version(pkg)
            _startup_log(f"  {disp} v{ver} ✓", "OK")
        except importlib.metadata.PackageNotFoundError:
            _startup_log(f"  {disp} missing, installing...", "WARN")
            ok, output = _pip_install([pkg])
            if ok:
                try:
                    ver = importlib.metadata.version(pkg)
                    _startup_log(f"  {disp} v{ver} installed ✓", "OK")
                except Exception:
                    _startup_log(f"  {disp} install verify failed ✗", "WARN")
            else:
                _startup_log(f"  {disp} install failed: {output}", "WARN")
        except Exception as e:
            _startup_log(f"  {disp} check failed: {e}", "WARN")

    # Set WHISPER_AVAILABLE flag
    try:
        import faster_whisper
        WHISPER_AVAILABLE = True
        _startup_log("faster_whisper loaded ✓ — Whisper engine available", "OK")
    except ImportError:
        WHISPER_AVAILABLE = False
        _startup_log("faster_whisper NOT available — Whisper engine disabled", "WARN")

# Run dependency checks
_ensure_packages()
_install_optional_packages()

# =========================
# CONFIG & PERSISTENCE
# =========================
CONFIG_FILE = os.path.join(BASE_DIR, "vtt_settings.json")

_startup_log(f"VTT Startup — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
_startup_log(f"OS: {platform.platform()}")
_startup_log(f"Python: {sys.version.split()[0]} ({struct.calcsize('P') * 8}-bit)")
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
    "engine": "google",
    "whisper_model": "base",
    "whisper_pause": "1.5s",
    "wake_word_enabled": False,
    "wake_word": "hey vtt",
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

        # Whisper engine state
        self.whisper_model = None
        self.transcription_queue = queue.Queue()
        self.vad_speaking = False
        self.vad_buffer = []
        self.vad_last_speech = 0.0
        self.whisper_worker_thread = None

        # Wake word state
        self.wake_listener_running = False
        self.wake_listener_thread = None

        self.setup_ui()
        self.attributes("-topmost", self.config.get("always_on_top", False))
        self.update_threshold()
        self.bind("<Configure>", self.save_pos)
        self.bind_all("<Key>", self._on_key, add="+")
        self._load_hotkey()

        # Start wake word listener if enabled
        if self.config.get("wake_word_enabled", False):
            self._start_wake_listener()

    # ---- File logging (writes every event to logs.txt) ----
    def _file_log(self, category, message, level="INFO"):
        """Write an event to the persistent log file."""
        _write_log(f"[{level}] [{category}] {message}")

    # ---- UI ----
    def setup_ui(self):
        ctk.CTkLabel(self, text="VTT", font=("Impact", 45)).pack(pady=(15, 0))
        self.lbl_powered = ctk.CTkLabel(self, text="", font=("Arial", 10), text_color="grey")
        self.lbl_powered.pack(pady=(0, 10))
        self._update_powered_by_label()

        self.btn_run = ctk.CTkButton(self, text="START VOICE ENGINE", height=45, fg_color="#27AE60", font=("Arial", 15, "bold"), command=self.toggle_vtt)
        self.btn_run.pack(pady=10, padx=35, fill="x")

        self.auto_enter_var = tk.BooleanVar(value=self.config.get("auto_enter", False))
        ctk.CTkCheckBox(self, text="Enable Auto-Enter", variable=self.auto_enter_var, command=self.sync_auto).pack(pady=5)

        ctk.CTkButton(self, text="⚙ SETTINGS", width=120, command=self.open_settings).pack(pady=10)

        self.lbl_status = ctk.CTkLabel(self, text="● IDLE", text_color="grey")
        self.lbl_status.pack()

        # Wake word indicator (shown when wake word is enabled)
        self.lbl_wake = ctk.CTkLabel(self, text="", font=("Arial", 9), text_color="#8E44AD")
        self.lbl_wake.pack(pady=(2, 0))
        self._update_wake_label()

        self.lbl_about = ctk.CTkLabel(self, text="About", font=("Arial", 11, "underline"), text_color="grey", cursor="hand2")
        self.lbl_about.pack(side="bottom", pady=(0, 0))
        self.lbl_about.bind("<Button-1>", lambda e: self.show_about())

    def _update_wake_label(self):
        if self.config.get("wake_word_enabled", False):
            ww = self.config.get("wake_word", "hey vtt")
            if self.running:
                self.lbl_wake.configure(text="")
            else:
                self.lbl_wake.configure(text=f"🎤 Listening: \"{ww}\"")
        else:
            self.lbl_wake.configure(text="")

    def on_closing(self):
        self._file_log("System", "App closing")
        self.running = False
        self.wake_listener_running = False
        self._clear_hotkey()
        self.destroy()
        _write_log("=== Session End ===\n")
        try: _LOG_FH.close()
        except: pass
        os._exit(0)

    def update_threshold(self):
        sens_map = {"High": 1400, "Medium": 550, "Low": 180}
        self.recognizer.energy_threshold = sens_map.get(self.config["sensitivity"], 550)

    @staticmethod
    def _rms_energy(audio_chunk):
        """Return RMS energy of int16 audio chunk (matches
        speech_recognition's internal energy calculation)."""
        data = audio_chunk.astype(np.float64)
        return np.sqrt(np.mean(np.square(data)))

    def _ensure_whisper_model(self):
        """Lazy-load the faster-whisper model. Returns True on success.
        On failure, reverts engine to google and returns False."""
        if self.whisper_model is not None:
            return True
        if not WHISPER_AVAILABLE:
            self.add_log("Whisper", "faster-whisper not installed", "ERROR")
            messagebox.showerror(
                "Whisper Unavailable",
                "faster-whisper is not installed.\n\n"
                "Run: pip install faster-whisper\n\n"
                "Falling back to Google Speech Recognition."
            )
            self.config["engine"] = "google"
            save_settings(self.config)
            self._update_powered_by_label()
            return False

        model_size = self.config.get("whisper_model", "base")
        try:
            from faster_whisper import WhisperModel
            self.add_log("Whisper", f"Loading {model_size} model (first use, downloading if needed)...")
            self.whisper_model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                num_workers=2,
            )
            self.add_log("Whisper", f"Model '{model_size}' loaded OK")
            return True
        except ImportError:
            self.add_log("Whisper", "faster-whisper not installed", "ERROR")
            messagebox.showerror(
                "Whisper Unavailable",
                "faster-whisper is not installed.\n\n"
                "Run: pip install faster-whisper\n\n"
                "Falling back to Google Speech Recognition."
            )
            self.config["engine"] = "google"
            save_settings(self.config)
            self._update_powered_by_label()
            return False
        except Exception as e:
            self.add_log("Whisper", f"Model load failed: {e}", "ERROR")
            messagebox.showerror(
                "Whisper Error",
                f"Could not load Whisper model '{model_size}'.\n\n"
                f"Error: {e}\n\n"
                "Check disk space and network. Falling back to Google."
            )
            self.config["engine"] = "google"
            save_settings(self.config)
            self._update_powered_by_label()
            return False

    def _update_powered_by_label(self):
        engine = self.config.get("engine", "google")
        if engine == "whisper":
            model = self.config.get("whisper_model", "base")
            self.lbl_powered.configure(text=f"Powered by Whisper ({model})")
        else:
            self.lbl_powered.configure(text="Powered by Google")

    def sync_auto(self):
        self.config["auto_enter"] = self.auto_enter_var.get()
        save_settings(self.config)

    def center_on_parent(self, win, w, h):
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def show_about(self):
        about = ctk.CTkToplevel(self)
        about.transient(self)
        about.title("About VTT")
        about.resizable(False, False)
        self.center_on_parent(about, 280, 180)

        ctk.CTkLabel(about, text="VTT", font=("Impact", 36)).pack(pady=(20, 0))
        ctk.CTkLabel(about, text="v2.0.0", font=("Arial", 12)).pack()
        ctk.CTkLabel(about, text="Voice to Text - by jlaiii", font=("Arial", 11), text_color="grey").pack(pady=(10, 5))
        lbl_gh = ctk.CTkLabel(about, text="github.com/jlaiii/VTT", font=("Arial", 11, "underline"),
                              text_color="#3498DB", cursor="hand2")
        lbl_gh.pack()
        lbl_gh.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/jlaiii/VTT"))

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        self.center_on_parent(self.settings_window, 420, 580)
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.focus_force()

    def add_log(self, category, message, level="INFO"):
        """Log to both the GUI log window AND the file."""
        # File log (always active after startup)
        self._file_log(category, message, level)

        # GUI log (if window is open)
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

    # ================================================================
    # WAKE WORD LISTENER
    # ================================================================
    def _start_wake_listener(self):
        """Start a background thread that listens for the wake word.
        Uses Google STT for fast, accurate wake word detection.
        When detected, toggles the engine ON."""
        if self.wake_listener_running:
            return
        ww = self.config.get("wake_word", "hey vtt").strip().lower()
        if not ww:
            return
        self.wake_listener_running = True
        self._update_wake_label()
        self._file_log("Wake", f"Wake word listener started — listening for \"{ww}\"")
        self.wake_listener_thread = threading.Thread(target=self._wake_listener_loop, args=(ww,), daemon=True)
        self.wake_listener_thread.start()

    def _stop_wake_listener(self):
        self.wake_listener_running = False
        self.lbl_wake.configure(text="")
        self._file_log("Wake", "Wake word listener stopped")

    def _wake_listener_loop(self, wake_word):
        """Continuously listen for the wake word via Google STT.
        Only runs while engine is OFF."""
        rec = sr.Recognizer()
        rec.energy_threshold = self.recognizer.energy_threshold
        rec.pause_threshold = 1.0
        rec.phrase_threshold = 0.3

        with sr.Microphone(sample_rate=16000) as source:
            rec.adjust_for_ambient_noise(source, duration=1)
            self._file_log("Wake", "Microphone calibrated for wake word detection")

            while self.wake_listener_running:
                # Only listen when engine is OFF (avoids double-transcription)
                if self.running:
                    time.sleep(0.5)
                    continue

                try:
                    # Listen for a short phrase
                    audio = rec.listen(source, timeout=5, phrase_time_limit=3)
                    text = rec.recognize_google(audio).lower().strip()
                    self._file_log("Wake", f"Heard: \"{text}\" (checking for \"{wake_word}\")")

                    if wake_word in text:
                        self._file_log("Wake", f"Wake word MATCH! Toggling engine ON")
                        # Use after() to safely call from background thread
                        self.after(0, self._on_wake_word)
                except sr.WaitTimeoutError:
                    # No speech detected — loop continues
                    continue
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    continue
                except Exception as e:
                    self._file_log("Wake", f"Listener error: {e}", "WARN")
                    time.sleep(0.5)

    def _on_wake_word(self):
        """Called on the main thread when wake word is detected."""
        if not self.running:
            self._file_log("Wake", "Voice-activating engine")
            self.toggle_vtt()

    # ================================================================
    # ENGINE TOGGLE & THREAD MANAGEMENT
    # ================================================================
    def toggle_vtt(self):
        if not self.running:
            self.running = True
            engine = self.config.get("engine", "google")

            # Lazy-load whisper model if needed
            if engine == "whisper":
                if not self._ensure_whisper_model():
                    engine = "google"  # fallback after failed load

            self.btn_run.configure(text="STOP VOICE ENGINE", fg_color="#C0392B")
            self.lbl_status.configure(text="● ACTIVE", text_color="#2ecc71")
            self.last_speech_time = time.time()
            self.add_log("System", f"Engine Online ({engine.title()})")
            self._update_wake_label()

            # Start threads — audio capture is always the same
            threading.Thread(target=self.audio_capture, daemon=True).start()
            threading.Thread(target=self.processor, daemon=True).start()
            threading.Thread(target=self.enter_logic, daemon=True).start()
            threading.Thread(target=self.idle_monitor, daemon=True).start()

            # Whisper-specific: start transcription worker
            if engine == "whisper":
                self.whisper_worker_thread = threading.Thread(
                    target=self._whisper_worker, daemon=True
                )
                self.whisper_worker_thread.start()
        else:
            self.stop_engine()

    def stop_engine(self):
        self.running = False
        # Drain queues to unblock any waiting threads
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        while not self.transcription_queue.empty():
            try:
                self.transcription_queue.get_nowait()
            except queue.Empty:
                break
        # Reset VAD state
        self.vad_speaking = False
        self.vad_buffer = []
        # UI updates
        self.btn_run.configure(text="START VOICE ENGINE", fg_color="#27AE60")
        self.lbl_status.configure(text="● IDLE", text_color="grey")
        self.add_log("System", "Engine Offline")
        self._update_wake_label()

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
        except Exception as e:
            self.add_log("Audio", f"Capture stream failed: {e}", "ERROR")
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
        """Dispatcher: route to Google or Whisper processor based on config."""
        engine = self.config.get("engine", "google")
        if engine == "whisper" and WHISPER_AVAILABLE and self.whisper_model is not None:
            self._processor_whisper()
        else:
            self._processor_google()

    def _processor_whisper(self):
        """VAD-based utterance segmentation for Whisper.
        Accumulates audio during speech, pushes complete WAV to
        transcription_queue when silence > pause_threshold."""
        fs = 16000
        pause_map = {"1.0s": 1.0, "1.5s": 1.5, "2.0s": 2.0}
        pause_sec = pause_map.get(self.config.get("whisper_pause", "1.5s"), 1.5)
        min_utterance_samples = int(fs * 0.3)  # ignore utterances < 0.3s

        while self.running:
            if not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                energy = self._rms_energy(chunk)

                if energy > self.recognizer.energy_threshold:
                    # Speech detected
                    if not self.vad_speaking:
                        self.vad_speaking = True
                        self.vad_buffer = []
                    self.vad_buffer.append(chunk)
                    self.vad_last_speech = time.time()
                elif self.vad_speaking:
                    # Was speaking, still below threshold — keep buffering
                    self.vad_buffer.append(chunk)
                    gap = time.time() - self.vad_last_speech
                    if gap > pause_sec:
                        # Utterance boundary reached
                        total_samples = sum(c.shape[0] for c in self.vad_buffer)
                        if total_samples >= min_utterance_samples:
                            full = np.concatenate(self.vad_buffer, axis=0)
                            byte_io = io.BytesIO()
                            write(byte_io, fs, full)
                            byte_io.seek(0)
                            self.transcription_queue.put(byte_io)
                            self._file_log("VAD", f"Utterance captured ({total_samples/fs:.1f}s)")
                        self.vad_speaking = False
                        self.vad_buffer = []
            else:
                time.sleep(0.05)

    def _whisper_worker(self):
        """Continuously pull utterance WAVs from transcription_queue,
        run faster-whisper inference, and type the result."""
        while self.running:
            try:
                wav_io = self.transcription_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                from scipy.io.wavfile import read as wav_read
                wav_io.seek(0)
                sr_check, audio_np = wav_read(wav_io)
                # audio_np is int16; faster-whisper wants float32 in [-1, 1]
                if audio_np.ndim > 1:
                    audio_np = audio_np.flatten()
                audio_fp = audio_np.astype(np.float32) / 32768.0

                self._file_log("Whisper", f"Transcribing {len(audio_fp)/16000:.1f}s of audio...")
                segments, info = self.whisper_model.transcribe(
                    audio_fp,
                    beam_size=5,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(
                        threshold=0.5,
                        min_speech_duration_ms=250,
                    ),
                )

                full_text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
                if full_text:
                    self.add_log("Heard", f'"{full_text}"')
                    pyautogui.write(full_text + " ",
                                    interval=float(self.config["delay"].replace('s', '')))
                    self.last_speech_time = time.time()
                    self.enter_pending = True
            except Exception as ex:
                self.add_log("Whisper", f"Inference error: {ex}", "ERROR")

    def _processor_google(self):
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
    # Model specs for display
    MODEL_SPECS = {
        "tiny":   "39M params | ~1 GB VRAM | ~10x speed",
        "base":   "74M params | ~1 GB VRAM | ~7x speed",
        "small":  "244M params | ~2 GB VRAM | ~4x speed",
        "medium": "769M params | ~5 GB VRAM | ~2x speed",
        "large":  "1550M params | ~10 GB VRAM | 1x speed",
        "turbo":  "809M params | ~6 GB VRAM | ~8x speed (recommended)",
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.parent = parent
        self.title("Settings")
        self.geometry("420x580")
        self.resizable(False, False)

        # Buttons packed FIRST (bottom) — always visible, never scroll
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=(4, 8))
        ctk.CTkButton(btn_frame, text="LOGS", width=100, command=self.open_logs).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="SAVE", width=100, command=self.apply, fg_color="#27AE60", height=38).pack(side="right", padx=5)

        # Scrollable content fills the remaining space above buttons
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(side="top", fill="both", expand=True, padx=5, pady=(5, 0))

        DROP_W = 280  # wide enough for "Google Speech Recognition"

        # --- Typing Speed ---
        ctk.CTkLabel(self.scroll, text="Typing Speed:").pack(pady=(10, 0))
        self.speed_drop = ctk.CTkComboBox(self.scroll, width=DROP_W, values=["0.0s", "0.01s", "0.05s", "0.1s"])
        self.speed_drop.pack(); self.speed_drop.set(parent.config["delay"])

        # --- Mic Sensitivity ---
        ctk.CTkLabel(self.scroll, text="Mic Sensitivity:").pack(pady=(8, 0))
        self.sens_drop = ctk.CTkComboBox(self.scroll, width=DROP_W, values=["High", "Medium", "Low"])
        self.sens_drop.pack(); self.sens_drop.set(parent.config["sensitivity"])

        # --- Speech Engine ---
        ctk.CTkLabel(self.scroll, text="Speech Engine:").pack(pady=(8, 0))
        engine_values = ["Google Speech Recognition", "Whisper (Local)"]
        self.engine_drop = ctk.CTkComboBox(
            self.scroll, width=DROP_W, values=engine_values, command=self._on_engine_change
        )
        self.engine_drop.pack()
        current_engine = parent.config.get("engine", "google")
        self.engine_drop.set(
            "Google Speech Recognition" if current_engine == "google"
            else "Whisper (Local)"
        )

        # --- Whisper Model (conditional) ---
        self.whisper_model_label = ctk.CTkLabel(self.scroll, text="Whisper Model:")
        self.whisper_model_drop = ctk.CTkComboBox(
            self.scroll, width=DROP_W,
            values=["tiny", "base", "small", "medium", "large", "turbo"],
            command=self._on_model_change
        )
        self.whisper_model_drop.set(parent.config.get("whisper_model", "base"))
        # Model specs info line
        self.whisper_specs_label = ctk.CTkLabel(
            self.scroll, text="", font=("Arial", 10), text_color="#888888"
        )
        self._update_model_specs(self.whisper_model_drop.get())

        # --- Whisper VAD Silence (conditional) ---
        self.whisper_pause_label = ctk.CTkLabel(self.scroll, text="VAD Silence (utterance end):")
        self.whisper_pause_drop = ctk.CTkComboBox(
            self.scroll, width=DROP_W, values=["1.0s", "1.5s", "2.0s"]
        )
        self.whisper_pause_drop.set(parent.config.get("whisper_pause", "1.5s"))

        # --- Auto-Enter Delay ---
        ctk.CTkLabel(self.scroll, text="Auto-Enter Delay:").pack(pady=(8, 0))
        self.delay_drop = ctk.CTkComboBox(self.scroll, width=DROP_W, values=["3s", "5s", "8s", "30s", "1m"])
        self.delay_drop.pack(); self.delay_drop.set(parent.config["enter_delay"])

        # --- Idle Auto-Stop ---
        ctk.CTkLabel(self.scroll, text="Idle Auto-Stop:").pack(pady=(8, 0))
        self.idle_drop = ctk.CTkComboBox(self.scroll, width=DROP_W, values=["10s", "30s", "60s", "Never"])
        self.idle_drop.pack(); self.idle_drop.set(parent.config.get("idle_stop", "Never"))

        # --- Always on Top ---
        self.always_top_var = tk.BooleanVar(value=parent.config.get("always_on_top", False))
        self.always_top_cb = ctk.CTkCheckBox(self.scroll, text="Always on Top", variable=self.always_top_var, command=self._toggle_always_top)
        self.always_top_cb.pack(pady=(12, 3))

        # --- Toggle Hotkey ---
        ctk.CTkLabel(self.scroll, text="Toggle Hotkey:").pack(pady=(8, 0))
        hotkey_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hotkey_frame.pack(pady=3)
        self.hotkey_entry = ctk.CTkEntry(hotkey_frame, width=160, placeholder_text="e.g. ctrl+shift+v")
        self.hotkey_entry.pack(side="left", padx=(0, 5))
        self.hotkey_entry.insert(0, parent.config.get("toggle_hotkey", ""))
        self.hotkey_entry.bind("<Key>", lambda e: "break")
        self.hotkey_entry.bind("<KeyRelease>", self._capture_hotkey)
        self._recording_hotkey = False
        ctk.CTkButton(hotkey_frame, text="RECORD", width=60, command=self._start_hotkey_record).pack(side="left")

        # --- Wake Word ---
        self.wake_enabled_var = tk.BooleanVar(value=parent.config.get("wake_word_enabled", False))
        self.wake_enabled_cb = ctk.CTkCheckBox(
            self.scroll, text="Enable Wake Word (voice activation)",
            variable=self.wake_enabled_var, command=self._on_wake_toggle
        )
        self.wake_enabled_cb.pack(pady=(12, 0))

        self.wake_word_label = ctk.CTkLabel(self.scroll, text="Wake Phrase:")
        self.wake_word_entry = ctk.CTkEntry(self.scroll, width=200, placeholder_text="e.g. hey vtt")
        self.wake_word_entry.insert(0, parent.config.get("wake_word", "hey vtt"))
        self._on_wake_toggle()  # show/hide based on current setting

        # Show/hide Whisper settings based on current engine
        self._on_engine_change(self.engine_drop.get())

    def _update_model_specs(self, model_name):
        spec = self.MODEL_SPECS.get(model_name, "")
        self.whisper_specs_label.configure(text=spec)

    def _on_model_change(self, choice):
        self._update_model_specs(choice)

    def _toggle_always_top(self):
        self.parent.set_always_on_top(self.always_top_var.get())

    def _on_wake_toggle(self):
        if self.wake_enabled_var.get():
            self.wake_word_label.pack(pady=(5, 0))
            self.wake_word_entry.pack()
        else:
            self.wake_word_label.pack_forget()
            self.wake_word_entry.pack_forget()

    def _on_engine_change(self, choice):
        is_whisper = "Whisper" in choice
        if is_whisper:
            self.whisper_model_label.pack(pady=(8, 0))
            self.whisper_model_drop.pack()
            self.whisper_specs_label.pack()
            self.whisper_pause_label.pack(pady=(8, 0))
            self.whisper_pause_drop.pack()
        else:
            self.whisper_model_label.pack_forget()
            self.whisper_model_drop.pack_forget()
            self.whisper_specs_label.pack_forget()
            self.whisper_pause_label.pack_forget()
            self.whisper_pause_drop.pack_forget()

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
        engine_value = "google" if "Google" in self.engine_drop.get() else "whisper"
        old_wake = self.parent.config.get("wake_word_enabled", False)
        new_wake = self.wake_enabled_var.get()
        new_wake_word = self.wake_word_entry.get().strip()

        self.parent.config.update({
            "delay": self.speed_drop.get(),
            "enter_delay": self.delay_drop.get(),
            "sensitivity": self.sens_drop.get(),
            "idle_stop": self.idle_drop.get(),
            "engine": engine_value,
            "whisper_model": self.whisper_model_drop.get(),
            "whisper_pause": self.whisper_pause_drop.get(),
            "wake_word_enabled": new_wake,
            "wake_word": new_wake_word if new_wake_word else "hey vtt",
        })
        save_settings(self.parent.config)
        self.parent.update_threshold()
        self.parent._update_powered_by_label()

        # Handle wake word listener state changes
        if not old_wake and new_wake:
            self.parent._start_wake_listener()
            self.parent.add_log("Settings", f"Wake word enabled: \"{new_wake_word or 'hey vtt'}\"")
        elif old_wake and not new_wake:
            self.parent._stop_wake_listener()
            self.parent.add_log("Settings", "Wake word disabled")
        elif old_wake and new_wake and new_wake_word != self.parent.config.get("wake_word", ""):
            # Wake word phrase changed — restart listener
            self.parent._stop_wake_listener()
            self.parent._start_wake_listener()
            self.parent.add_log("Settings", f"Wake word updated: \"{new_wake_word}\"")

        self.parent._update_wake_label()
        self.destroy()

class DebugWindow(ctk.CTkToplevel):
    def __init__(self, settings_parent, main_parent):
        super().__init__(settings_parent)
        self.transient(settings_parent)
        self.title("System Logs")
        self.geometry("450x350")

        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        ctk.CTkButton(self, text="OPEN LOGS FILE", height=28, width=140,
                      command=lambda: os.startfile(LOGS_PATH) if sys.platform == "win32" else None).pack(pady=(5, 8))

        main_parent.log_widget = self.log_box
        main_parent.flush_startup_logs()

if __name__ == "__main__":
    try:
        _write_log("Boot: entering mainloop")
        VTT().mainloop()
    except Exception:
        tb = traceback.format_exc()
        _write_log(f"FATAL:\n{tb}")
        try: _LOG_FH.close()
        except: pass
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("VTT Fatal Error", f"Check logs.txt next to VTT.pyw\n\n{tb.splitlines()[-1]}")
        except:
            pass
        sys.exit(1)
    finally:
        try: _LOG_FH.close()
        except: pass
