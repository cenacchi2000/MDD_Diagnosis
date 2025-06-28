import asyncio

ROBOT_STATE = system.import_library("../../../HB3/robot_state.py")
robot_state = ROBOT_STATE.state

async def robot_say(text: str) -> None:
    """Speak through the robot's TTS with console fallback."""
    print(f"[Ameca]: {text}")
    try:
        robot_state.last_language_code = "eng"
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass


async def robot_listen() -> str:
    """Listen for speech and return the recognized text."""
    while True:
        speech_task = asyncio.create_task(system.wait_for_event("speech_recognized"))
        no_speech_task = asyncio.create_task(system.wait_for_event("no_speech_heard"))

        done, pending = await asyncio.wait(
            {speech_task, no_speech_task},
            timeout=10,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

        if speech_task in done:
            try:
                evt = speech_task.result()
                text = evt.get("text") if isinstance(evt, dict) else getattr(evt, "text", "")
                if text:
                    return text.strip()
            except Exception:
                pass

        await robot_say("I didn't catch that, please repeat.")
