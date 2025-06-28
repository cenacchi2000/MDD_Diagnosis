from typing import Any, Optional
from dataclasses import dataclass

SpeechRecognitionClient = system.import_library(
    "../Perception/lib/asr_client.py"
).SpeechRecognitionClient

ROBOT_STATE = system.import_library("../robot_state.py")
robot_state = ROBOT_STATE.state

TYPES = system.import_library("types.py")
BACKEND = "cartesia_ai_tts_v1"


MINIMUM_CLONEABLE_UTTERANCE_BYTE_LENGTH = 70


@dataclass
class VoiceCloningInfo:
    error: Optional[str] = None
    retry: bool = False
    speech_event: Optional[Any] = None


def get_voice_cloning_info() -> VoiceCloningInfo:
    for info in robot_state.available_tts_voices or []:
        if info.backend == BACKEND:
            break
    else:
        return VoiceCloningInfo(
            error="no available backend supports cloning", retry=False
        )
    speech_event = ROBOT_STATE.interaction_history.last_recognized_speech_event()
    if not speech_event:
        return VoiceCloningInfo(error="no speech event to clone from", retry=True)

    if speech_event.id is None:
        log.info(
            "missing speech id, is voice_id set to true in the speech recognition node? Or is the software too old?"
        )
        return VoiceCloningInfo(
            error="missing speech id, software too old", retry=False
        )

    # TODO: Combine several utterances or at least iterate through older utterances to improve on this.
    # Would require voice id to be accurate?
    if len(speech_event.speech.encode()) < MINIMUM_CLONEABLE_UTTERANCE_BYTE_LENGTH:
        return VoiceCloningInfo(error="users speech was too short", retry=True)

    return VoiceCloningInfo(speech_event=speech_event)


def can_clone_user_voice() -> bool:
    for info in robot_state.available_tts_voices:
        if info.backend == BACKEND:
            return (
                ROBOT_STATE.interaction_history.last_recognized_speech_event()
                is not None
            )
    return False


async def clone_user_voice(info: Optional[VoiceCloningInfo] = None):
    if info is None:
        info = get_voice_cloning_info()
        if info.error:
            raise RuntimeError(f"Can't clone voice: {info.error}")
    # TODO: this client should be the same instance as the one used by Add_Speech.py
    asr_client = SpeechRecognitionClient(system.unstable.owner)
    cloned_voice = await asr_client.clone_voice(info.speech_event.id, BACKEND)
    log.info(f"Cloned user voice from phrase: {info.speech_event.speech!r}")
    return TYPES.TTSVoiceInfo(
        name=cloned_voice,
        engine="Service Proxy",
        backend=BACKEND,
    )