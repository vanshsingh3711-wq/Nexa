from fastapi import FastAPI
from contextlib import asynccontextmanager

from input.gesture.gesture_manager import GestureManager
from input.voice.voice_listener import VoiceListener
from core.commands.event_router import EventRouter

# Global application lifecycle objects
router = EventRouter()
gesture_manager = GestureManager(event_router=router)
router.gesture_manager = gesture_manager
voice_listener: VoiceListener | None = None

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

    def _on_wake():
        router.wake_nexa()

    def _on_close():
        def _cleanup():
            voice_listener.stop()
            gesture_manager.stop()
        router.close_nexa(cleanup_fn=_cleanup)

    def _on_gesture(active, text):
        gesture_manager.start() if active else gesture_manager.stop()

    def _on_command(cmd, params=None):
        router.execute_action(cmd, params=params, source="voice")

    def _on_confirm():
        router.confirm_pending()

    def _on_cancel():
        router.cancel_pending()

    voice_listener = VoiceListener(
        on_nexa_wake=_on_wake,
        on_nexa_close=_on_close,
        on_gesture_mode_change=_on_gesture,
        on_command=_on_command,
        on_confirm=_on_confirm,
        on_cancel=_on_cancel
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
        "voice_active": voice_listener.is_running if voice_listener else False,
        "is_user_speaking": voice_listener.is_user_speaking if voice_listener else False,
        "last_action_timestamp": router.last_action_timestamp
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False, access_log=False)
