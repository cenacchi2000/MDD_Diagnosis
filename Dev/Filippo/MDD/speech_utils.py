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
            print("[WARN] Failed to send TTS message")

async def robot_listen() -> str:
    """Return the next transcribed utterance from the speech recognizer."""
    if system is None:
        while True:
            text = input("> ").strip()
            if text:
                return text
            print("[Ameca]: I didn't catch that, please repeat.")
    else:
        async with system.world.query_features(name="speech_recognition") as sub:
            async for evt in sub.async_iter():
                evt_type = getattr(evt, "type", None)
                if evt_type == "speech_recognized":
                    text = getattr(evt, "text", "")
                    if isinstance(evt, dict):
                        text = evt.get("text", "")
                    text = text.strip()
                    if text:
                        return text
                    await robot_say("I didn't catch that, please repeat.")

