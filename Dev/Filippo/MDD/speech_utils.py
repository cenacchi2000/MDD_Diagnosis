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
    while True:
        try:
            evt = await system.wait_for_event("speech_recognized")
        except Exception:
            evt = None

        if isinstance(evt, dict):
            text = evt.get("text", "").strip()
            if text:
                return text

        await robot_say("I didn't catch that, please repeat.")
