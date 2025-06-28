"""Keeps track of the robot's state."""

import asyncio
from typing import Optional, Awaitable
from itertools import count
from collections import deque

import numpy as np

INTERACTION_HISTORY = system.import_library("./chat/knowledge/interaction_history.py")
CHAT_CONFIG = system.import_library("../Config/Chat.py").CONFIG
PERSONA_UTIL = system.import_library("./lib/persona_util.py")

TYPES = system.import_library("./lib/types.py")

loop = asyncio.get_event_loop()

interaction_history = INTERACTION_HISTORY.InteractionHistory()
interaction_history.register_hooks(
    ["ASR", "TTS", "non_verbal"]
)  # ASR, TTS, and non_verbal events will be automatic added to this history

known_voice_ids: dict[str, deque[np.ndarray]] = {}


class RobotState:

    # Whether or not the robot is currently saying something
    speaking: bool = False
    # Whether or not the robot is blinking
    blinking: bool = False
    # What the robot is saying
    currently_saying: Optional[TYPES.SpeechItem] = None

    # Whether or not the robot is thinking of a response
    is_thinking: bool = False

    # Whether the robot is currently looking for cameras and posing in response
    is_camera_tracking: bool = False

    # The robot can use default voices - uses the voices from the map according to current language
    # Or using alternate - uses the set alternate voice until it is reset back to default
    uses_default_voices: bool = True

    # If it is using an alternate voice, this is the voice it is using
    current_alternate_voice: Optional[TYPES.TTSVoiceInfo] = None

    # Default mapping of languages it can do to the voices it should use. The robot only speak languages in this map
    # This map is populated from the persona
    # Value is None if voice is not available in TTS node
    default_language_voice_map: dict[str, Optional[TYPES.TTSVoiceInfo]] = (
        {}
    )  # key is language code in ISO 639-3

    # All available voices, from TTS node
    available_tts_voices: list[TYPES.TTSVoiceInfo] = []

    # The last language code the robot spoke in, used for thinking sounds language
    last_language_code: Optional[str] = "eng"

    def set_currently_saying(self, speech_item, probe=None):
        if speech_item:
            self.currently_saying = speech_item
            self.speaking = True
            self.last_language_code = speech_item.language_code
            system.messaging.post("tts_saying", speech_item)
        elif self.speaking:
            self.currently_saying = None
            self.speaking = False
            system.messaging.post("tts_idle", None)

        if probe:
            probe(
                "currently_saying",
                self.currently_saying.speech if self.currently_saying else None,
            )
            probe("speaking", self.speaking)

    # A set of tasks currently responding to user requests
    response_task: Optional[asyncio.Task] = None
    process_task: dict[int, asyncio.Task] = {}

    response_task_id_counter = count()
    process_task_id_counter = count()

    def start_response_task(self, awaitable: Awaitable, cancel_previous: bool = True):
        """Start a new task for the robot to respond to something.

        The default behavior is to replace an existing response_task which exists (see `cancel_previous`)

        Args:
            awaitable: the new response task
            cancel_previous (bool, optional): if this is True, any previous response task will be cancelled and replaced with this one.
            Else, an error is thrown if there is already a task. Defaults to True.

        Returns:
            the response task
        """
        id = next(self.response_task_id_counter)
        log.info(f"[RESPONSE TASK {id}] starting")
        if self.response_task:
            if cancel_previous:
                self.cancel_response_task()
            else:
                raise Exception(
                    "Attempt to start a new response task with `cancel_previous=False` when there is already an existing task"
                )
        loop = asyncio.get_event_loop()
        task = loop.create_task(awaitable)
        self.response_task = task

        def clear_task(cb_future: asyncio.Task):
            try:
                cb_future.result()  # handle exception
                if cb_future.cancelled():
                    log.info(f"[RESPONSE TASK {id}] cancelled")
                else:
                    log.info(f"[RESPONSE TASK {id}] finished")
            except asyncio.CancelledError:
                log.info(f"[RESPONSE TASK {id}] cancelled")
            except Exception:
                log.exception("Unexpected error occurred in response task")

            if self.response_task is task:
                self.response_task = None

        task.add_done_callback(clear_task)
        return task

    def cancel_response_task(self):
        if self.response_task:
            self.response_task.cancel()
            self.response_task = None
        else:
            log.warning(
                "Attempt to cancel response task ignored as there was no response task running."
            )

    def start_process_task(self, awaitable: Awaitable):
        """Start a new task. The task should not make a response directly.

        Args:
            awaitable: the new response task

        Returns:
            the task
        """
        id = next(self.process_task_id_counter)
        log.info(f"[PROCESS TASK {id}] starting")
        loop = asyncio.get_event_loop()
        task = loop.create_task(awaitable)
        self.process_task[id] = task

        def clear_task(cb_future: asyncio.Future):
            if id in self.process_task:
                try:
                    self.process_task.pop(id)
                    cb_future.result()  # handle exceptions
                    if cb_future.cancelled():
                        log.info(f"[PROCESS TASK {id}] cancelled")
                    else:
                        log.info(f"[PROCESS TASK {id}] finished")
                except asyncio.CancelledError:
                    log.info(f"[PROCESS TASK {id}] cancelled")
                except Exception:
                    log.exception("Unexpected error occurred in process task")

        task.add_done_callback(clear_task)
        return task

    def cancel_process_task(self, id: int):
        if id in self.process_task:
            self.self.process_task[id].cancel()
        else:
            log.warning(f"Attempt to cancel unknown process task {id}.")

    # Whether or not the robot is in the thinking pose
    is_thinking: bool = False

    def set_thinking(self, value):
        self.is_thinking = value
        system.messaging.post("is_thinking", value)

    # TTS Voices Functions

    def set_available_tts_voices(self, value: Optional[list[TYPES.TTSVoiceInfo]]):
        if value is None:
            log.warning("No available TTS models found, resetting voice settings")
            self.uses_default_voices = True
            self.current_alternate_voice = None
            self.default_language_voice_map = {}
            self.available_tts_voices = []
            return

        self.available_tts_voices = value

        persona_language_voice_map_cache: Optional[dict[str, TYPES.TTSVoiceInfo]] = None

        # iterate over current language map, and warn if any of them is not in the available TTS models
        for language in self.default_language_voice_map:

            voice = self.default_language_voice_map[language]

            # Voice was previously unavailable, check to see if it is now available by refetching from persona
            if voice is None:
                if persona_language_voice_map_cache is None:
                    persona_language_voice_map_cache = (
                        PERSONA_UTIL.get_language_voice_map()
                    )
                voice = persona_language_voice_map_cache[language]

            # Voice is unavailable, warn and mark it as unavailable (by setting to None)
            if voice not in self.available_tts_voices:
                log.warning(
                    f"Voice {voice} for language {language} from persona voices is not in available TTS models"
                )
                self.default_language_voice_map[language] = None

    def set_default_language_voice_map(
        self, language_voice_map: dict[str, TYPES.TTSVoiceInfo]
    ):
        self.default_language_voice_map = language_voice_map

    @property
    def default_language(self) -> str:
        """
        The default language of the robot in ISO 639-3 format. This is set as the first language in the map from personas.
        """
        return next(iter(self.default_language_voice_map.keys()))

    @property
    def all_languages(self) -> set[str]:
        """
        Returns all the languages the robot can currently speak, taken from the default_language_voice_map
        """
        return set(self.default_language_voice_map.keys())

    def _get_fallback_voice(self) -> Optional[TYPES.TTSVoiceInfo]:
        """
        Returns the fallback voice to use if the voice it should use is not available
        """
        fallback_voices = [
            TYPES.TTSVoiceInfo(**voice) for voice in CHAT_CONFIG["FALLBACK_TTS_VOICES"]
        ]

        for fallback_voice in fallback_voices:
            if fallback_voice in self.available_tts_voices:
                return fallback_voice
        return None

    def get_voice_for_language(self, language: str) -> Optional[TYPES.TTSVoiceInfo]:
        if self.uses_default_voices:
            # check if the language is in map
            if language in self.default_language_voice_map:
                voice = self.default_language_voice_map[language]
                if voice is None:
                    log.warning(
                        f"Voice for language {language} is not available, using fallback voice"
                    )
            else:
                voice = None
                log.warning(
                    f"Language {language} is not available, using fallback voice"
                )

            if voice is None:
                fallback = self._get_fallback_voice()
                log.info(f"Using fallback voice: {fallback}")
                return fallback
            return voice
        else:
            voice = self.current_alternate_voice

            if isinstance(voice.name, str) and voice not in self.available_tts_voices:
                # Name is string - normal voice (not voice cloning), and not available from the TTS node
                log.warning(
                    f"Current alternate voice {voice} is not available, using fallback voice"
                )
                fallback = self._get_fallback_voice()
                log.info(f"Using fallback voice: {fallback}")
                return fallback

            return voice

    def reset_to_default_voice(self):
        self.uses_default_voices = True
        self.current_alternate_voice = None

    def activate_alternate_tts_voice(self, voice: TYPES.TTSVoiceInfo | dict):
        if isinstance(voice, dict):
            voice = TYPES.TTSVoiceInfo(**voice)
        if isinstance(voice.name, str) and voice not in self.available_tts_voices:
            log.warning(f"Attempted to activate invalid voice: {voice}")
            raise RuntimeError(f"activate_alternate_tts_voice: Invalid voice: {voice}")

        self.current_alternate_voice = voice
        self.uses_default_voices = False


state = RobotState()