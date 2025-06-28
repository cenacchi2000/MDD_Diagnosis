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
        speech_task = asyncio.create_task(
            system.wait_for_event("speech_recognized", timeout=10)
        )
        no_speech_task = asyncio.create_task(
            system.wait_for_event("no_speech_heard", timeout=10)
        )

        done, pending = await asyncio.wait(
            {speech_task, no_speech_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

        if speech_task in done:
            try:
                evt = speech_task.result()
                if isinstance(evt, dict):
                    text = evt.get("text", "").strip()
                    if text:
                        return text
            except Exception:
                pass

        print("[Ameca]: I didn't catch that, please repeat.")
