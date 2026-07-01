from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.services.desktop_automation import desktop_automation
from app.services.screen_understanding import screen_understanding
from app.services.voice_service import voice_service

router = APIRouter(prefix="/desktop", tags=["Desktop & Voice Automation"])

class DesktopActionRequest(BaseModel):
    action: str
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    keys: Optional[List[str]] = None

class VoiceProcessRequest(BaseModel):
    text: str

@router.post("/action")
def trigger_desktop_action(request: DesktopActionRequest):
    """Trigger mouse clicks, cursor moves, keyboard typings, or hotkeys."""
    try:
        if request.action == "move":
            return desktop_automation.move_mouse(request.x or 0, request.y or 0)
        elif request.action == "click":
            return desktop_automation.click_mouse(request.x, request.y)
        elif request.action == "type":
            return desktop_automation.type_keyboard(request.text or "")
        elif request.action == "hotkey":
            return desktop_automation.press_hotkey(request.keys or [])
        elif request.action == "clipboard_read":
            return desktop_automation.get_clipboard()
        elif request.action == "clipboard_write":
            return desktop_automation.set_clipboard(request.text or "")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action parameter: {request.action}")
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))

@router.get("/screenshot")
def capture_active_screen():
    """Retrieve base64 screenshot data stream of active workspace."""
    return {"status": "success", "image": screen_understanding.capture_screen_base64()}

@router.post("/voice/tts")
def process_voice_tts(request: VoiceProcessRequest):
    """Synthesize text inputs to base64 audio mp3 streams."""
    audio_base64 = voice_service.process_text_to_speech(request.text)
    return {"status": "success", "audio": audio_base64}
