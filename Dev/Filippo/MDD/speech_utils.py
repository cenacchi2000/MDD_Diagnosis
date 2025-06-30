import asyncio
from typing import Optional

try:
    from tritium.client.client import Client
except Exception:  # pragma: no cover - optional dependency
    Client = None  # type: ignore[assignment]

try:
    system  # type: ignore[name-defined]
except NameError:  # allow running outside the robot system
    system = None

_tts_client: Optional[Client] = None
_tts_done: Optional[asyncio.Event] = None
_asr_client: Optional[object] = None  # SpeechRecognitionClient type not required


async def _ensure_tts():
    global _tts_client, _tts_done
    if _tts_client is None and Client is not None and getattr(system, "unstable", None):
        _tts_client = Client(owner=system.unstable.owner, name="Text To Speech")
        _tts_done = asyncio.Event()

        def _on_tts_event(msg):
            if isinstance(msg, dict) and msg.get("type") == "play_finished":
                _tts_done.set()

        _tts_client.subscribe_to(
            _tts_client.make_address("events"),
            _on_tts_event,
            expect_json=True,
            description="TTS events",
        )


async def robot_say(text: str) -> None:
    """Speak through the robot's TTS with console fallback."""
    print(f"[Ameca]: {text}")

    await _ensure_tts()
    if _tts_client is not None and _tts_done is not None:
        _tts_done.clear()
        try:
            _tts_client.send_api("say", text=text, voice="Amy", engine="Service Proxy")
            await asyncio.wait_for(_tts_done.wait(), timeout=10)
            return
        except Exception:
            print("[WARN] Failed to use TTS client")

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
            try:
                text = input("> ")
            except EOFError:
                # In non-interactive environments input() can raise EOFError.
                # Returning an empty string allows the caller to handle the
                # missing input gracefully instead of crashing.
                return ""
            text = text.strip()
            if text:
                return text
            print("[Ameca]: I didn't catch that, please repeat.")
    else:
        global _asr_client
        if _asr_client is None and Client is not None and getattr(system, "unstable", None):
            SpeechRecognitionClient = system.import_library("../../../HB3/Perception/lib/asr_client.py").SpeechRecognitionClient
            _asr_client = SpeechRecognitionClient(system.unstable.owner)

        if _asr_client is not None:
            _asr_client.start_speech_recognition()

        async with world.query_features(name="speech_recognition") as sub:
            async for evt in sub.async_iter():
                evt_type = getattr(evt, "type", None)
                if evt_type == "speech_recognized":
                    text = getattr(evt, "text", "")
                    if isinstance(evt, dict):
                        text = evt.get("text", "")
                    text = text.strip()
                    if text:
                        if _asr_client is not None:
                            _asr_client.stop_speech_recognition()
                        return text
                    await robot_say("I didn't catch that, please repeat.")

