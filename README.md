# Nexa - Multi-Hand Gesture & Voice Controlled Assistant

Nexa is an intelligent desktop automation and interaction assistant driven by real-time computer vision (MediaPipe) hand gesture recognition and voice command activation.

## Features

- **Multi-Hand Real-time Gesture Recognition**: Powered by MediaPipe Hand Landmarker.
- **Dynamic Gesture Classification**: Supports custom pinch, swipe, open palm, peace, and fist gestures.
- **Spatial & Temporal Stability Filtering**: Smooth landmark filtering and debounce for jitter-free trigger handling.
- **Voice Activation**: Hands-free voice listener trigger ("Hey Nexa" activation modes).
- **System & Media Automation**:
  - Media Controls: Play, Pause, Next Track, Previous Track
  - System Volume: Volume Up, Volume Down, Mute/Unmute
  - Mouse Navigation & Click Emulation
  - Browser Shortcuts & Tab Navigation
- **FastAPI Core**: Modular backend architecture with extensible event routing.

## Project Structure

```text
Nexa/
├── backend/
│   ├── actions/          # Automation modules (media, mouse, volume, system)
│   ├── core/             # Event router and core orchestration
│   ├── input/
│   │   ├── gesture/      # Camera feed, landmarker, classifier, stability filter
│   │   └── voice/        # Voice recognition and activation listener
│   ├── main.py           # FastAPI application entrypoint
│   ├── requirements.txt  # Python dependencies
│   ├── test_camera.py    # Real-time gesture visualization test
│   └── test_gestures_unit.py # Gesture pipeline unit tests
├── .gitignore
└── README.md
```

## Supported Gestures & Controls

| Gesture | Movement | Action |
| :--- | :--- | :--- |
| **Open Palm (5 Fingers)** | Swipe Up | **Open Task View / Tab Page** (`Win + Tab`) |
| **3 Fingers (Index+Middle+Ring)** | Swipe Left | **Browser Back** (`Alt + Left`) |
| **3 Fingers (Index+Middle+Ring)** | Swipe Right | **Browser Forward** (`Alt + Right`) |
| **2 Fingers (Peace)** | Swipe Right | **Select Next Tab / Window** |
| **2 Fingers (Peace)** | Swipe Left | **Select Previous Tab / Window** |
| **Pinch (Thumb + Index)** | Touch tips | **Enter / Open Selected Tab** (in Tab Mode) / **Left Click** (Mouse Mode) |
| **Index Finger (1 Finger)** | Point & Move | **Move Mouse Cursor** |
| **Closed Fist** | Hold | **Toggle Play / Pause** |
| **Thumb Up** | Point Up | **Volume Up** |
| **Thumb Down** | Point Down | **Volume Down** |

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Webcam for gesture tracking
- Microphone for voice activation

### 2. Setup Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate     # On Windows
# source venv/bin/activate # On macOS/Linux
pip install -r requirements.txt
```

### 3. Run Camera Gesture Test
```bash
python test_camera.py
```

### 4. Run Server
```bash
python main.py
```

