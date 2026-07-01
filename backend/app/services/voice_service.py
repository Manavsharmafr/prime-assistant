import os
from typing import Dict, Any, Optional

class VoiceService:
    def verify_wake_word(self, phrase: str) -> bool:
        """Analyze if input voice phrases contain wake word keys."""
        normalized = phrase.lower()
        return any(trigger in normalized for trigger in ["hey prime", "prime assistant", "wake up prime", "hi prime"])

    def process_speech_to_text(self, audio_data: bytes) -> str:
        """Transcribe speech audio data streams to text. (Mock/Local offline template fallback)"""
        # Under local emulation, we resolve incoming mock audio data to standard default actions
        return "Hey Prime, show stats and read screen"

    def process_text_to_speech(self, text: str) -> str:
        """Synthesize text responses into Base64 audio mp3 streams for speech output."""
        # Clean up text logs
        clean_text = text.replace('"', '').replace('\n', ' ')
        
        # Return a deterministic small dummy MP3/WAV header base64 payload to prevent player crashes
        dummy_base64_audio = (
            "data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        return dummy_base64_audio

voice_service = VoiceService()
