from fastapi import FastAPI
from contextlib import asynccontextmanager

from input.gesture.gesture_manager import GestureManager
from input.voice.voice_listener import VoiceListener
from core.commands.event_router import EventRouter

# Global application lifecycle objects
router = EventRouter()
gesture_manager = GestureManager(event_router=router)
router.gesture_manager = gesture_manager
voice_listener: VoiceListener = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup & shutdown lifespan.
    Notice: Camera and MediaPipe are NOT initialized during startup.
    VoiceListener starts so users can say 'Wake up Nexa', 'Enable gestures', or 'Close Nexa'.
    """
    global voice_listener
    
    print("\n" + "="*50)
    print("🚀 NEXA BACKEND STARTED")
    print("🎤 Say 'Wake up Nexa' to activate Nexa.")
    print("🖐️ Say 'Enable gestures' to start the webcam on demand.")
    print("🚪 Say 'Close Nexa' to safely close.")
    print("="*50 + "\n")

    voice_listener = VoiceListener(
        on_nexa_wake=lambda: router.wake_nexa(),
        on_nexa_close=lambda: router.close_nexa(cleanup_fn=lambda: (voice_listener.stop(), gesture_manager.stop())),
        on_gesture_mode_change=lambda active, text: gesture_manager.start() if active else gesture_manager.stop(),
        on_command=lambda cmd, params=None: router.execute_action(cmd, params=params, source="voice")
    )
    voice_listener.start()
    
    yield
    
    print("\n[Nexa] Shutting down application...")
    if voice_listener:
        voice_listener.stop()
    gesture_manager.stop(speak_feedback=False)
    print("[Nexa] Shutdown complete.")

app = FastAPI(title="Nexa Desktop Assistant API", lifespan=lifespan)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "nexa_active": router.is_nexa_active,
        "gestures_active": gesture_manager.is_active,
        "voice_active": voice_listener.is_running if voice_listener else False
    }

@app.get("/gesture")
def get_current_gesture():
    """Returns the latest recognized gesture data."""
    return gesture_manager.get_current_gesture()

@app.get("/gesture/status")
def get_gesture_status():
    """Returns whether the on-demand gesture subsystem and camera are active."""
    return {
        "is_active": gesture_manager.is_active,
        "camera_released": not gesture_manager.is_active
    }

@app.post("/gesture/start")
def start_gestures():
    """Explicitly enables gesture tracking and starts the webcam."""
    success = gesture_manager.start()
    return {"success": success, "is_active": gesture_manager.is_active}

@app.post("/gesture/stop")
def stop_gestures():
    """Explicitly disables gesture tracking and completely releases the webcam."""
    success = gesture_manager.stop()
    return {"success": success, "is_active": gesture_manager.is_active}

@app.post("/nexa/wake")
def wake_nexa():
    """Activates Nexa application state."""
    success = router.wake_nexa()
    return {"success": success, "nexa_active": router.is_nexa_active}

@app.post("/nexa/close")
def close_nexa():
    """Initiates clean Nexa application shutdown."""
    success = router.close_nexa()
    return {"success": success, "nexa_active": router.is_nexa_active}
