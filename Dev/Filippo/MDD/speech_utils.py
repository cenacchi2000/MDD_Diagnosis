import asyncio

async def robot_say(text: str) -> None:
    """Speak through the robot's TTS with console fallback."""
    print(f"[Ameca]: {text}")
    try:
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass

async def robot_listen() -> str:
    """Return the next transcribed utterance from the speech recognizer."""
    try:
        evt = await system.wait_for_event("speech_recognized")
        if isinstance(evt, dict):
            return evt.get("text", "").strip()
    except Exception:
        pass
    return ""
