import sys, os, threading, time, json, traceback, io, queue, random, tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import speech_recognition as sr
import pyautogui
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import difflib

# =========================
# CONFIG & PERSISTENCE
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "vtt_settings.json")

DEFAULT_SETTINGS = {
    "auto_enter": False, 
    "enter_delay": "3s",
    "delay": "0.01s",
    "sensitivity": "Medium",
    "idle_stop": "Never",
    "last_x": 100,
    "last_y": 100
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
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.running = False
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        
        # FINE-TUNED PRECISION:
        self.recognizer.pause_threshold = 2.0  
        self.recognizer.phrase_threshold = 0.3 # Lowered to catch "Enter" vs "Answer" better
        self.recognizer.non_speaking_duration = 0.8 
        
        self.last_sent_words = [] 
        self.last_speech_time = time.time()
        self.enter_pending = False
        self.settings_window = None
        self.log_widget = None
        self.log_window = None
        
        self.setup_ui()
        self.update_threshold()
        self.bind("<Configure>", self.save_pos)

    def on_closing(self):
        self.running = False
        self.destroy()
        os._exit(0)

    def update_threshold(self):
        sens_map = {"High": 1400, "Medium": 550, "Low": 180}
        self.recognizer.energy_threshold = sens_map.get(self.config["sensitivity"], 550)

    def save_pos(self, event):
        if not self.running:
            self.config["last_x"], self.config["last_y"] = self.winfo_x(), self.winfo_y()
            save_settings(self.config)

    def setup_ui(self):
        ctk.CTkLabel(self, text="VTT", font=("Impact", 45)).pack(pady=(15, 0))
        ctk.CTkLabel(self, text="Powered by Google", font=("Arial", 10), text_color="grey").pack(pady=(0, 10))
        
        self.btn_run = ctk.CTkButton(self, text="START BOT", height=45, fg_color="#27AE60", font=("Arial", 15, "bold"), command=self.toggle_vtt)
        self.btn_run.pack(pady=10, padx=35, fill="x")
        
        self.auto_enter_var = tk.BooleanVar(value=self.config.get("auto_enter", False))
        ctk.CTkCheckBox(self, text="Enable Auto-Enter", variable=self.auto_enter_var, command=self.sync_auto).pack(pady=5)
        
        ctk.CTkButton(self, text="⚙ SETTINGS", width=120, command=self.open_settings).pack(pady=10)
        
        self.lbl_status = ctk.CTkLabel(self, text="● IDLE", text_color="grey")
        self.lbl_status.pack()

    def sync_auto(self):
        self.config["auto_enter"] = self.auto_enter_var.get()
        save_settings(self.config)

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self)
        self.settings_window.attributes("-topmost", True)
        self.settings_window.lift()

    def add_log(self, category, message):
        if self.log_widget and self.log_widget.winfo_exists():
            clean_msg = f"{category.upper()}: {message}\n"
            self.log_widget.insert("end", clean_msg)
            self.log_widget.see("end")

    def toggle_vtt(self):
        if not self.running:
            self.running = True
            self.btn_run.configure(text="STOP ENGINE", fg_color="#C0392B")
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
        self.btn_run.configure(text="START BOT", fg_color="#27AE60")
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
        except: self.running = False

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
                    except: buffer = buffer[-int(fs * 0.2):]
            else: time.sleep(0.05)

# =========================
# WINDOWS
# =========================
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Settings")
        self.geometry("340x520")
        self.attributes("-topmost", True)
        
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
        
        ctk.CTkButton(self, text="LOGS", command=self.open_logs).pack(pady=15)
        ctk.CTkButton(self, text="SAVE", command=self.apply, fg_color="#27AE60", height=40).pack(pady=10)
        
    def open_logs(self):
        if self.parent.log_window is None or not self.parent.log_window.winfo_exists():
            self.parent.log_window = DebugWindow(self.parent)
        self.parent.log_window.attributes("-topmost", True)
        self.parent.log_window.lift()

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
    def __init__(self, parent):
        super().__init__(parent)
        self.title("System Logs")
        self.geometry("450x350")
        self.attributes("-topmost", True)
        
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        
        ctk.CTkButton(self, text="CLEAR", height=28, width=80, fg_color="#34495E", 
                      command=lambda: self.log_box.delete("1.0", "end")).pack(pady=5)
        parent.log_widget = self.log_box

if __name__ == "__main__":
    VTT().mainloop()