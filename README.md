# VTT — Voice to Text Engine

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="MIT">
  <img src="https://img.shields.io/badge/Speech-Google%20%7C%20Whisper-orange?style=flat" alt="Speech Engines">
  <img src="https://img.shields.io/badge/Version-2.0.0-purple?style=flat" alt="v2.0.0">
</p>

**VTT** is a lightweight Windows desktop app that transcribes your voice into keystrokes in real time — no accounts, no subscriptions. Talk and it types into any application: terminal, editor, browser, anywhere.

> Now with **local Whisper support** — run entirely offline. Your audio never leaves your machine.

---

## Features

- **Two speech engines**: Google Speech Recognition (fast, online) and Whisper (local, offline)
- **Real-time typing** — speaks through your mic, types into any active window
- **Wake word** — say *"hey vtt"* to activate hands-free
- **Hotkey toggle** — bind any key combo to start/stop the engine
- **Smart deduplication** — filters out repeated words and stutters (Google engine)
- **Auto-Enter** — presses Enter after configurable silence delay
- **Idle auto-stop** — engine shuts off after inactivity
- **Always on Top** — keep VTT visible over any window
- **System logs** — everything logged to `logs.txt`

---

## Quick Start

### Option 1: One-Click (recommended)

Double-click **`start.bat`** — it finds Python, installs missing packages, and launches VTT. No configuration needed.

### Option 2: Manual

```bash
git clone https://github.com/jlaiii/VTT.git
cd VTT

# Install required packages
pip install customtkinter SpeechRecognition PyAutoGUI sounddevice numpy scipy keyboard

# (Optional) For local Whisper engine
pip install faster-whisper

# Launch (no console window)
pythonw VTT.pyw
```

---

## Requirements

| Package | Purpose |
|---------|---------|
| `customtkinter` | Modern dark-themed GUI |
| `SpeechRecognition` | Google STT backend |
| `PyAutoGUI` | OS keystroke injection |
| `sounddevice` | Low-latency mic capture |
| `numpy`, `scipy` | Audio processing |
| `keyboard` | Global hotkey registration |
| `faster-whisper` | Local Whisper engine *(optional)* |

---

## Settings

| Setting | Options | Description |
|---------|---------|-------------|
| Typing Speed | 0.0s – 0.1s | Keystroke delay |
| Mic Sensitivity | High / Medium / Low | Background noise adjustment |
| Speech Engine | Google / Whisper | Recognition backend |
| Whisper Model | tiny / base / small / medium / large / turbo | Local model (VRAM tradeoff) |
| VAD Silence | 1.0s – 2.0s | Pause before utterance ends |
| Auto-Enter Delay | 3s – 1m | Silence before Enter pressed |
| Idle Auto-Stop | 10s – Never | Auto-shutoff timer |
| Always on Top | yes / no | Keep window visible |
| Toggle Hotkey | e.g. ctrl+shift+v | Keyboard shortcut |
| Wake Word | e.g. "hey vtt" | Voice activation phrase |

---

## Whisper Models

| Model | Params | VRAM | Relative Speed | Best For |
|-------|--------|------|----------------|----------|
| tiny | 39M | ~1 GB | ~10x | Edge / low-memory |
| base | 74M | ~1 GB | ~7x | Balanced **(default)** |
| small | 244M | ~2 GB | ~4x | Better accuracy |
| medium | 769M | ~5 GB | ~2x | Production quality |
| large | 1550M | ~10 GB | 1x | Max accuracy |
| turbo | 809M | ~6 GB | ~8x | Fast + accurate ★ |

*Whisper runs entirely on your CPU. No internet, no API keys, no data leaves your machine.*

---

## How It Works

### Google Engine
```
Mic → 16kHz stream → 1.8s sliding windows (0.6s overlap) → Google STT API → dedup → type
```
Fast, accurate, requires internet.

### Whisper Engine
```
Mic → 16kHz stream → VAD detects speech → accumulates utterance → silence gap → faster-whisper transcribes → type
```
Utterance-based segmentation with VAD. Local, offline, private.

---

## Project Structure

```
VTT/
├── VTT.pyw              Main application (double-click to run)
├── start.bat            One-click launcher (auto Python + dep install)
├── README.md            This file
├── logs.txt             Session logs (auto-created)
├── vtt_settings.json    User preferences (auto-created)
└── .vtt_deps_ok         Package cache marker (auto-created)
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
  <sub>Built by <a href="https://github.com/jlaiii">jlaiii</a> · <a href="https://jlaiii.github.io/VTT/">Website</a> · v2.0.0</sub>
</div>
