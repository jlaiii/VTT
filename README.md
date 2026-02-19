# VTT (Voice-To-Text) Automation Engine

An asynchronous Python application powered by the Google Speech Recognition API, designed to convert real-time vocal input into automated keyboard strokes. This project focuses on high-precision transcription and seamless integration with the operating system's input layer.

---

## Overview
VTT is a specialized utility that bridges the gap between speech recognition and desktop automation. By utilizing the Google Web Speech API and the pyautogui library, the application allows for hands-free text entry into any active software environment.

### Core Functionalities
* **Google-Powered Transcription**: Leverages Google's speech-to-text engine for high-accuracy vocal analysis.
* **Asynchronous Audio Processing**: Employs Python threading and queue management to handle concurrent audio capture and text processing without UI latency.
* **Dynamic Deduplication**: Implements a sequence matching algorithm via the difflib library to filter redundant phrases and improve transcription clarity.
* **Intelligent Auto-Submit**: Features a configurable "Auto-Enter" logic that triggers a return key command after a specified duration of silence.
* **Persistent Configuration**: Automatically tracks and stores user preferences, including window coordinates and hardware sensitivity, in a local JSON schema.

---

## Technical Architecture
* **Speech Engine**: Utilizes the SpeechRecognition library specifically configured for Google's recognition services.
* **Interface**: Developed using customtkinter for a high-DPI, modern graphical user interface.
* **Audio Engineering**: Uses sounddevice and numpy for low-latency signal processing and audio buffering.
* **Automation**: Utilizes pyautogui for direct OS-level character injection.

---

## Configuration Details
| Parameter | Function |
| :--- | :--- |
| Typing Speed | Controls the interval between injected characters to ensure compatibility with target applications. |
| Mic Sensitivity | Adjusts the energy threshold for the Google recognizer to account for background noise. |
| Idle Auto-Stop | A safety feature that deactivates the engine after a period of inactivity to conserve system resources. |
| System Logs | A real-time debug window providing transparency into the audio processing and recognition pipeline. |

---

## Installation and Usage

1. **Clone the Repository**:
   ```bash
   git clone [https://github.com/YourUsername/VTT.git](https://github.com/YourUsername/VTT.git)
   cd VTT
