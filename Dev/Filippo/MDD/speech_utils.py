import asyncio

try:
    system  # type: ignore[name-defined]
except NameError:  # allow running outside the robot system
    system = None

async def robot_say(text: str) -> None:
    """Speak through the robot's TTS with console fallback."""
    print(f"[Ameca]: {text}")
    if system is not None:
        try:
            system.messaging.post("tts_say", [text, "eng"])
        except Exception:
            pass

async def robot_listen() -> str:
    """Return the next transcribed utterance from the speech recognizer."""
    while True:
        if system is not None:
            try:
                evt = await system.wait_for_event("speech_recognized")
            except Exception:
                evt = None

            if isinstance(evt, dict):
                text = evt.get("text", "").strip()
                if text:
                    return text

            await robot_say("I didn't catch that, please repeat.")
        else:
            text = input("> ").strip()
            if text:
                return text
