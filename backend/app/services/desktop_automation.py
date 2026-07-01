import os
import time
from typing import Dict, Any, List, Optional
from app.services.permission import permission_service

# Graceful import fallbacks for headless servers
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pyperclip
    PYCLIPBOARD_AVAILABLE = True
except ImportError:
    PYCLIPBOARD_AVAILABLE = False


class DesktopAutomationService:
    def _verify_safety(self, action: str, details: str):
        """Enforce command whitelists / blocklists safety policies."""
        if action == "dangerous_hotkey":
            raise PermissionError(f"Desktop automation hotkey '{details}' is blocked by safety policy.")

        risk_level, justification = permission_service.check_permission(f"desktop_automation_{action} {details}")
        if risk_level == "blocked":
            raise PermissionError(f"Desktop automation action '{action}' on target '{details}' blocked by safety policy: {justification}")

    def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        details = f"Coordinates: X={x}, Y={y}"
        self._verify_safety("move", details)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.moveTo(x, y, duration=0.5)
                return {"status": "success", "message": f"Moved mouse to ({x}, {y})"}
            except Exception as err:
                return {"status": "emulated", "message": f"Mouse move failed: {str(err)}"}
        return {"status": "emulated", "message": f"Emulated mouse move to ({x}, {y}) (PyAutoGUI not loaded)"}

    def click_mouse(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> Dict[str, Any]:
        coords = f"Coordinates: X={x}, Y={y}" if x is not None else "Current position"
        details = f"{button} click at {coords}"
        self._verify_safety("click", details)

        if PYAUTOGUI_AVAILABLE:
            try:
                if x is not None and y is not None:
                    pyautogui.click(x, y, button=button)
                else:
                    pyautogui.click(button=button)
                return {"status": "success", "message": f"Performed {button} mouse click"}
            except Exception as err:
                return {"status": "emulated", "message": f"Mouse click failed: {str(err)}"}
        return {"status": "emulated", "message": f"Emulated {button} click (PyAutoGUI not loaded)"}

    def type_keyboard(self, text: str) -> Dict[str, Any]:
        # Truncate content in logs for privacy/safety
        logged_text = text[:15] + "..." if len(text) > 15 else text
        self._verify_safety("type", logged_text)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.write(text, interval=0.05)
                return {"status": "success", "message": "Typed text on keyboard"}
            except Exception as err:
                return {"status": "emulated", "message": f"Keyboard typing failed: {str(err)}"}
        return {"status": "emulated", "message": f"Emulated keyboard typing of '{logged_text}'"}

    def press_hotkey(self, keys: List[str]) -> Dict[str, Any]:
        details = "+".join(keys)
        # Block high risk hotkeys (Alt+F4, Ctrl+Alt+Del, etc.)
        has_alt = any(k.lower() == "alt" for k in keys)
        has_f4 = any(k.lower() == "f4" for k in keys)
        has_delete = any(k.lower() in ["delete", "del"] for k in keys)
        
        if (has_alt and has_f4) or has_delete:
            self._verify_safety("dangerous_hotkey", details)
        self._verify_safety("hotkey", details)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey(*keys)
                return {"status": "success", "message": f"Pressed hotkey: {details}"}
            except Exception as err:
                return {"status": "emulated", "message": f"Hotkey execution failed: {str(err)}"}
        return {"status": "emulated", "message": f"Emulated hotkey: {details}"}

    def get_clipboard(self) -> Dict[str, Any]:
        self._verify_safety("clipboard_read", "")
        if PYCLIPBOARD_AVAILABLE:
            try:
                val = pyperclip.paste()
                return {"status": "success", "content": val}
            except Exception as err:
                return {"status": "emulated", "content": f"Clipboard read failed: {str(err)}"}
        return {"status": "emulated", "content": "Emulated clipboard content (pyperclip not loaded)"}

    def set_clipboard(self, text: str) -> Dict[str, Any]:
        self._verify_safety("clipboard_write", "")
        if PYCLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(text)
                return {"status": "success", "message": "Copied text to clipboard"}
            except Exception as err:
                return {"status": "emulated", "message": f"Clipboard copy failed: {str(err)}"}
        return {"status": "emulated", "message": "Emulated clipboard copy"}

desktop_automation = DesktopAutomationService()
