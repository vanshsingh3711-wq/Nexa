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

## Supported Voice Commands

| Voice Command | Action | System Hotkey |
| :--- | :--- | :--- |
| **"Wake up"** / **"Start Nexa"** / **"Mode On"** | Resume Listening & Activate Gestures | Active Mode (Controlling PC) |
| **"Sleep"** / **"Stop Nexa"** / **"Mode Off"** | Pause Listening & Deactivate Gestures | Idle Mode (Sleeping) |

| **"Play"** / **"Resume"** | Play Media Stream | Media Play |
| **"Pause"** | Pause Media Stream | Media Pause |
| **"Play pause"** | Toggle Play / Pause | Media Play/Pause |
| **"Volume up"** | Increase System Volume | `Volume Up` |
| **"Volume down"** | Decrease System Volume | `Volume Down` |
| **"Mute"** / **"Toggle mute"** | Mute / Unmute Audio | `Volume Mute` |
| **"Go back"** | Browser Back | `Alt + Left` |
| **"Go forward"** | Browser Forward | `Alt + Right` |
| **"Next tab"** | Next Browser Tab | `Ctrl + Tab` |
| **"Previous tab"** | Previous Browser Tab | `Ctrl + Shift + Tab` |
| **"Close tab"** | Close Active Tab | `Ctrl + W` |
| **"Refresh page"** | Reload Current Web Page | `Ctrl + R` |
| **"Zoom in"** | Magnify Browser / App | `Ctrl + +` |
| **"Zoom out"** | Zoom Out Browser / App | `Ctrl + -` |
| **"Reset zoom"** | Reset Default Zoom (100%) | `Ctrl + 0` |
| **"Take screenshot"** | Capture and Save Screenshot | Direct / `Win + PrtScn` |
| **"Open task view"** | Open Windows Task View | `Win + Tab` |
| **"Next window"** | Select Next Window | `Right Arrow` |
| **"Previous window"** | Select Previous Window | `Left Arrow` |
| **"Select"** | Confirm Selected Window | `Enter` |




## On-Demand Gesture & Camera Lifecycle

To optimize battery, CPU, and RAM while protecting user privacy:
- **Zero Idle Resource Usage**: When gesture mode is OFF, the webcam is completely closed (`cv2.VideoCapture` released, hardware LED off) and MediaPipe processing is halted.
- **On-Demand Activation**: The `GestureManager` initializes camera and detection threads only upon explicit user command (e.g. *"Enable gestures"*, *"Wake up"*, or `/gesture/start`).
- **Clean Shutdown**: Saying *"Disable gestures"*, *"Sleep"*, or calling `/gesture/stop` terminates the background pipeline thread, resets all gesture tracking state, and releases the OS camera device.

| Voice Lifecycle Command | Action | Subsystem State |
| :--- | :--- | :--- |
| **"Enable gestures"** / **"Wake up"** / **"Start gestures"** | Start Camera & Detection Pipeline | Camera **ACTIVE** |
| **"Disable gestures"** / **"Sleep"** / **"Stop gestures"** | Release Camera & Stop Pipeline | Camera **RELEASED (0% CPU/RAM)** |


## Selective Voice Feedback (TTS)

Nexa features an offline, asynchronous Text-to-Speech (TTS) verbal confirmation engine powered by Windows SAPI5 (`pyttsx3`).

- **Selective Lifecycle Speech**: Nexa does **NOT** speak after every normal desktop action. Normal commands (`play`, `pause`, `volume_up`, `next_tab`, mouse movements, etc.) execute silently so the user is not disturbed.
- **Dedicated Lifecycle Feedback**: Spoken feedback is strictly reserved for application and gesture subsystem lifecycle state changes.
- **Anti-Echo Isolation**: The `SpeechCoordinator` automatically blocks microphone input while Nexa speaks (plus a short cooldown), preventing Nexa from triggering its own voice listener.

| Lifecycle Trigger Event | Verbal Spoken Response | Notes |
| :--- | :--- | :--- |
| **"Wake up Nexa"** / Wake | *"Welcome, Vansh. How can I help?"* | Spoken once upon successful activation |
| **"Close Nexa"** / Exit | *"Alright, closing Nexa."* | Plays before clean application shutdown |
| **"Enable gestures"** / Mode On | *"Gesture control enabled."* | Spoken only if camera starts successfully |
| **"Disable gestures"** / Mode Off | *"Gesture control disabled."* | Spoken after camera release completes |



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

