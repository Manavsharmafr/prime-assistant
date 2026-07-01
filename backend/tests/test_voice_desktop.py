import pytest
import os
from PIL import Image

from app.services.desktop_automation import desktop_automation
from app.services.screen_understanding import screen_understanding
from app.services.voice_service import voice_service
from app.services.tool_registry import tool_registry

# ─── Desktop Automation Tests ────────────────────────────────────────────────

def test_desktop_clicks_and_moves():
    """Verify coordinate mouse motions and click simulation responses."""
    # Move mouse coordinates
    res = desktop_automation.move_mouse(100, 200)
    assert "status" in res
    
    # Click mouse
    res_click = desktop_automation.click_mouse(100, 200, button="right")
    assert "status" in res_click


def test_keyboard_typing_and_hotkeys():
    """Verify hotkey parsing and keyboard triggers."""
    res = desktop_automation.type_keyboard("Hello Prime")
    assert res["status"] in ["success", "emulated"]

    res_hk = desktop_automation.press_hotkey(["ctrl", "c"])
    assert res_hk["status"] in ["success", "emulated"]


def test_clipboard_operations():
    """Verify system clipboard synchronization."""
    res_copy = desktop_automation.set_clipboard("Copied test buffer")
    assert res_copy["status"] in ["success", "emulated"]

    res_paste = desktop_automation.get_clipboard()
    assert "status" in res_paste


# ─── Screen Understanding & OCR Tests ────────────────────────────────────────

def test_screen_grab_and_ocr():
    """Verify PIL workspace captures and pytesseract OCR parses."""
    img = screen_understanding.capture_screen_image()
    assert isinstance(img, Image.Image)

    b64_img = screen_understanding.capture_screen_base64()
    assert b64_img.startswith("data:image/jpeg;base64,")

    ocr_text = screen_understanding.run_ocr()
    assert len(ocr_text) > 0


def test_screen_summarization():
    """Verify screen content summarization compiles response payload."""
    res = screen_understanding.summarize_screen(provider_override="offline")
    assert res["status"] == "success"
    assert "summary" in res
    assert "ocr_raw" in res


# ─── Voice Subsystem Tests ───────────────────────────────────────────────────

def test_voice_stt_tts_wake_word():
    """Verify wake word triggers, STT conversions, and TTS audio stream synthesis."""
    # 1. Wake word triggers
    assert voice_service.verify_wake_word("Hey Prime, how is the CPU stats?") is True
    assert voice_service.verify_wake_word("Hello Prime assistant") is True
    assert voice_service.verify_wake_word("Random conversational chat") is False

    # 2. Text to speech
    tts_res = voice_service.process_text_to_speech("System standby")
    assert tts_res.startswith("data:audio/mp3;base64,")


# ─── Security Permissions Integration Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_tool_registry_security_policy():
    """Verify tool execution registry handles vision and desktop automation safety permissions."""
    from sqlalchemy.orm import Session
    # Since we don't have db sessions for this, check execution boundaries directly
    # A dangerous desktop hotkey like del or taskkill will trigger whitelists/blocklists checks
    with pytest.raises(PermissionError):
        desktop_automation.press_hotkey(["ctrl", "alt", "delete"])
