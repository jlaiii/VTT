# VTT — Voice to Text

Real-time speech-to-text dictation for any Windows application. Speak into your mic, text appears wherever your cursor is.

## Features

- **Two speech engines**: Google Speech Recognition (fast, online) and Whisper (local, offline)
- **Real-time typing** — speaks through your mic, types into any app (terminal, editor, browser)
- **Wake word** — say "hey vtt" to activate hands-free
- **Hotkey toggle** — bind a key combo to start/stop
- **Auto-enter** — presses Enter after a configurable silence delay
- **Idle auto-stop** — engine shuts off after inactivity
- **Always on top** — keep the window visible
- **System logs** — everything is logged to `logs.txt`

## Quick Start

### Option 1: One-Click Launcher (recommended)

Double-click **`start.bat`**. It finds Python, installs missing packages, and launches VTT — zero config.

### Option 2: Manual

```bash
# Install dependencies
pip install customtkinter SpeechRecognition PyAutoGUI sounddevice numpy scipy keyboard

# (Optional) For offline Whisper engine
pip install faster-whisper

# Launch
pythonw VTT.pyw
```

## Requirements

| Package | Purpose |
|---------|---------|
| `customtkinter` | GUI |
| `SpeechRecognition` | Google STT engine |
| `PyAutoGUI` | Typing into windows |
| `sounddevice` | Audio capture |
| `numpy`, `scipy` | Audio processing |
| `keyboard` | Global hotkeys |
| `faster-whisper` | Local Whisper engine *(optional)* |

## Settings

| Setting | Options | Description |
|---------|---------|-------------|
| Typing Speed | 0.0s – 0.1s | Delay between keystrokes |
| Mic Sensitivity | High / Medium / Low | Audio threshold |
| Speech Engine | Google / Whisper | Recognition backend |
| Whisper Model | tiny → turbo | Local model size (VRAM tradeoff) |
| VAD Silence | 1.0s – 2.0s | Pause before utterance ends |
| Auto-Enter Delay | 3s – 1m | Silence before Enter is pressed |
| Idle Auto-Stop | 10s – Never | Auto-shutoff after inactivity |
| Always on Top | yes/no | Keep window visible |
| Toggle Hotkey | e.g. ctrl+shift+v | Keyboard shortcut |
| Wake Word | e.g. "hey vtt" | Voice activation phrase |

## Whisper Models

| Model | Params | VRAM | Speed | Best for |
|-------|--------|------|-------|----------|
| tiny | 39M | ~1 GB | ~10x | Edge / low-memory |
| base | 74M | ~1 GB | ~7x | Balanced (default) |
| small | 244M | ~2 GB | ~4x | Better accuracy |
| medium | 769M | ~5 GB | ~2x | Production quality |
| large | 1550M | ~10 GB | 1x | Max accuracy |
| turbo | 809M | ~6 GB | ~8x | Fast + accurate ★ |

*Whisper runs entirely offline. Your audio never leaves your machine.*

## Project Files

```
VoiceToText/
├── VTT.pyw              Main application
├── start.bat            One-click launcher
├── vtt_settings.json    User settings (auto-created)
├── logs.txt             Session logs (auto-created)
└── README.md            This file
```

## Logs

Every session appends to `logs.txt` — startup checks, engine toggles, transcribed text, errors, and wake word detections. Open it from the Settings → LOGS → OPEN LOGS FILE button.

## Credits

by [jlaiii](https://github.com/jlaiii/VTT)
