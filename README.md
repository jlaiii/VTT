# VTT — Voice to Text Engine

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="MIT">
  <img src="https://img.shields.io/badge/Speech-Google_API-orange?style=flat&logo=google" alt="Google Speech">
</p>

**VTT** is a lightweight Windows desktop app that transcribes your voice into keystrokes in real time — no cloud subscriptions, no accounts, just talk and it types. Perfect for hands-free text input in any application.

> Powered by Google's Speech Recognition API. Built with performance and simplicity in mind.

---

## Features

- **Real-time voice typing** — speak naturally and watch words appear wherever your cursor is
- **Smart deduplication** — filters out repeated words and stutters automatically via difflib sequence matching
- **Auto-Enter** — configurable delay to press Enter after you finish speaking (3s to 1min)
- **Always on Top** — keep VTT visible over any window
- **Custom hotkeys** — bind any key combo to toggle the engine on/off
- **Auto-pip install** — missing dependencies are installed automatically on first launch
- **Detailed system logs** — full diagnostics for troubleshooting: startup checks, audio device scans, dependency verification
- **Persistent settings** — everything saves between sessions

---

## Quick Start

### Requirements

- **Windows 10/11**
- **Python 3.10+** — [Download](https://python.org/downloads)
- A microphone

### Install & Run

```bash
git clone https://github.com/jlaiii/VTT.git
cd VTT
python VTT.pyw
```

> VTT auto-installs missing packages on first run — just launch `VTT.pyw` and it handles the rest.

Double-click `VTT.pyw` to launch silently (no console window). The app runs as a compact floating window.

---

## Settings

| Setting | Description |
|---|---|
| **Typing Speed** | Delay between injected keystrokes (0.0s - 0.1s) |
| **Mic Sensitivity** | Adjust for quiet rooms vs noisy environments (Low/Medium/High) |
| **Auto-Enter Delay** | Wait time before auto-pressing Enter (3s - 1min) |
| **Idle Auto-Stop** | Auto-shutoff if no speech detected (10s - Never) |
| **Always on Top** | Keep VTT above all other windows |
| **Toggle Hotkey** | Bind a keyboard shortcut to start/stop the engine |

---

## Tech Stack

```
customtkinter    -> Modern dark-themed GUI
SpeechRecognition -> Google Web Speech API integration
sounddevice      -> Low-latency microphone capture via PortAudio
NumPy + SciPy    -> Audio signal processing
PyAutoGUI        -> OS-level keystroke injection
keyboard         -> Global hotkey registration
```

---

## How It Works

VTT uses a multi-threaded architecture:

1. **Audio Capture** — streams mic input at 16kHz into a ring buffer
2. **Speech Processing** — feeds 1.8s audio windows to Google's recognition API with 0.6s overlap for continuity
3. **Deduplication** — difflib sequence matching filters already-sent words
4. **Keystroke Injection** — PyAutoGUI types cleaned text into the active window

The UI remains responsive because all heavy work runs on background daemon threads.

---

## Project Structure

```
VTT/
|-- VTT.pyw              # Main application (double-click to run)
|-- requirements.txt     # Dependencies
|-- vtt_settings.json    # Auto-generated user preferences
|-- docs/
|   |-- index.html       # GitHub Pages website
```

---

## Build to EXE

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile VTT.pyw
```

---

## Contributing

Found a bug or have an idea? Open an [issue](https://github.com/jlaiii/VTT/issues) or submit a pull request.

---

<div align="center">
  <sub>Built by <a href="https://github.com/jlaiii">jlaiii</a> &middot; <a href="https://jlaiii.github.io/VTT/">Website</a></sub>
</div>
