import asyncio

try:
    system  # type: ignore[name-defined]
except NameError:  # allow running outside the robot system
    system = None

async def robot_say(text: str) -> None:
    """Speak through the robot's TTS with console fallback."""
    print(f"[Ameca]: {text}")
    messaging = getattr(system, "messaging", None)
    if messaging is not None:
        try:
            messaging.post("tts_say", [text, "eng"])
        except Exception:
            print("[WARN] Failed to send TTS message")

async def robot_listen() -> str:
    """Return the next transcribed utterance from the speech recognizer."""
    world = getattr(system, "world", None)
    if world is None:
        while True:
            text = input("> ").strip()
            if text:
                return text
            print("[Ameca]: I didn't catch that, please repeat.")
    else:
        async with world.query_features(name="speech_recognition") as sub:
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

