import asyncio
from time import time as unix_time
from typing import Optional
from dataclasses import field, dataclass

from tritium.client.client import Client

try:
    from tritium.state_engine import StateEngineClientMixin
    from tritium.state_engine.client.state.activity import Activity as _Activity
except ImportError:

    class StateEngineClientMixin:
        pass


TTSVoiceInfo = system.import_library("../../lib/types.py").TTSVoiceInfo

VISEMES_MODULE = system.import_library("./visemes.py")
INTERACTION_HISTORY = system.import_library(
    "../../chat/knowledge/interaction_history.py"
)
TYPES = system.import_library("../../lib/types.py")


@dataclass
class TTSClientItem:
    event: INTERACTION_HISTORY.TTSEvent
    tts_item_id: Optional[int] = None
    viseme_count: int = 0
    viseme_queue: VISEMES_MODULE.VisemeQueue = field(
        default_factory=VISEMES_MODULE.VisemeQueue
    )


class TextToSpeechNodeClient(StateEngineClientMixin, Client):
    tts_by_activity: dict[
        _Activity,
        TTSClientItem,
    ] = {}

    def __init__(
        self,
        owner,
        on_item_playback_started=None,
        on_item_playback_finished=None,
        on_heartbeat_changed=None,
        name="Text To Speech",
        api_address=None,
        **settings,
    ):
        super().__init__(owner=owner, name=name, api_address=api_address, **settings)
        self._clear_state()
        self.on_item_playback_started_callback = on_item_playback_started
        self.on_item_playback_finished_callback = on_item_playback_finished
        self.listen_to_heartbeat(None, on_heartbeat_changed)

        self.tts_event_handlers = {
            "synthesis_complete": self.on_tts_item_synthesis_complete,
            "play_started": self.on_tts_item_play_started,
            "play_finished": self.on_tts_item_play_finished,
        }
        self.events_socket = self.subscribe_to(
            self.make_address("events"),
            self.on_tts_event_message,
            expect_json=True,
            description="TTS events",
        )

        self._properties_update_tasks = {}

        self._state_listeners = system.unstable.state_engine.on_activity(
            "tts",
            on_properties_set=self._on_tts_properties_updated,
            on_stop=self._on_tts_activity_stopped,
        )

    @classmethod
    def _clear_state(cls):
        cls.tts_by_activity = {}

    @classmethod
    def _get_current_activity(cls):
        """
        WARNING this method is not implementable on virtual tts_client
        It should only be used as a private method
        """
        # Returns the latest activity which has started
        # Ie the one currently playing
        latest = None
        latest_time = 0
        for activity in cls.tts_by_activity.keys():
            t = activity.properties.get("audio_start_time", 0)
            if t > latest_time:
                latest = activity
                latest_time = t
        return latest

    @classmethod
    def get_current_sentence(cls, time):
        activity = cls._get_current_activity()
        if not activity:
            return None

        item = cls.tts_by_activity.get(activity)
        event = item.event
        if event and event.synch_words is not None:
            return event.get_said_at_time(time), item.tts_item_id
        return None

    @classmethod
    def get_current_viseme_queue(cls):
        activity = cls._get_current_activity()
        if not activity:
            return None

        item = cls.tts_by_activity.get(activity)
        return item.viseme_queue

    def on_tts_event_message(self, msg):
        if (tts_item_id := msg.get("tts_item_id")) and (
            event_type := msg.get("type", None)
        ):
            if event_type in self.tts_event_handlers.keys():
                self.tts_event_handlers[event_type](tts_item_id, msg)
        else:
            log.warning(f"Unexpected tts event message format. Got {msg}")

    def on_tts_item_play_started(self, tts_item_id, msg):
        audio_start_time = msg.get("audio_start_time", unix_time())

        event = None
        for client_item in TextToSpeechNodeClient.tts_by_activity.values():
            if client_item.tts_item_id == tts_item_id:
                event = client_item.event
                break

        self.on_item_playback_started_callback(tts_item_id, event, audio_start_time)

    def on_tts_item_synthesis_complete(self, tts_item_id, msg):
        duration = float(msg["duration"])
        if duration == 0:
            self.on_tts_item_play_finished(tts_item_id, {})

    def on_tts_item_play_finished(self, tts_item_id, msg):
        audio_finish_time = msg.get("audio_finish_time", unix_time())
        self.on_item_playback_finished_callback(tts_item_id, audio_finish_time)

    def _on_tts_properties_updated(self, activity_info):
        activity = activity_info.activity
        tts_item_id = activity.properties.get("tts_item_id")
        if tts_item_id is None:
            log.warning("updated activity has no tts_item_id")
            return

        if activity not in TextToSpeechNodeClient.tts_by_activity:
            log.info("Adding new tts activity!")
            # This item must have come from somewhere else
            # Add a tts event in
            tts_event = INTERACTION_HISTORY.TTSEvent(
                TYPES.TTSVoiceInfo(
                    activity.properties["voice"],
                    activity.properties.get("engine", "Unknown"),
                    activity.properties.get("backend", "Unknown"),
                ),
                TYPES.SpeechItem(
                    activity.properties["text"],
                    activity.properties.get("language", None),
                    False,
                    # item_id is only present for the Service Proxy backend
                    activity.properties.get("item_id") or tts_item_id,
                ),
            )
            tts_client_item = TTSClientItem(tts_event, tts_item_id)
            TextToSpeechNodeClient.tts_by_activity[activity] = tts_client_item
        else:
            tts_client_item = TextToSpeechNodeClient.tts_by_activity[activity]
            if tts_client_item.tts_item_id is None:
                tts_client_item.tts_item_id = tts_item_id

        async def inner():
            # Yield to wait for any other changes which have come at the same time
            await asyncio.sleep(0.001)
            properties = activity.properties
            if start_time := properties.get("audio_start_time"):
                visemes_adjusted = []
                if visemes := properties.get("visemes"):
                    visemes_adjusted = [
                        {
                            "time": start_time + v["time"],
                            "viseme": v["viseme"],
                        }
                        for v in visemes
                    ]

                if visemes_adjusted:
                    visemes_adjusted.sort(key=lambda x: x["time"])

                    # Dont add visemes if they were already in the queue
                    count = tts_client_item.viseme_count
                    if count > 0:
                        visemes_adjusted = visemes_adjusted[count:]

                    tts_client_item.viseme_queue.add_visemes(visemes_adjusted)
                    tts_client_item.viseme_count += len(visemes_adjusted)

                synch_words = []
                if (words := properties.get("words")) and (
                    text := properties.get("text")
                ):
                    for word in words:
                        synch_words.append(
                            (
                                start_time + word["time"],
                                text.encode()[: word["position_bytes"]].decode(),
                            )
                        )
                tts_client_item.event.synch_words = synch_words

        def _done_cb(task):
            if not task.cancelled():
                self._properties_update_tasks.pop(tts_item_id, None)

        # Only run for the most recent event - cancel any previous update tasks which are queued
        if tts_item_id in self._properties_update_tasks:
            self._properties_update_tasks[tts_item_id].cancel()
        task = asyncio.create_task(inner())
        self._properties_update_tasks[tts_item_id] = task
        task.add_done_callback(_done_cb)

    @classmethod
    def _on_tts_activity_stopped(cls, stop_info):
        activity = stop_info.activity
        start_time = activity.properties.get("audio_start_time")
        item = cls.tts_by_activity.pop(activity, None)

        if item is not None:
            item.event.stop(unix_time())

            if item.tts_item_id is not None and start_time is not None:
                system.messaging.post(
                    "tts_item_finished",
                    (
                        item.event.speech_item.speech,
                        item.tts_item_id,
                    ),
                )

    @classmethod
    def say(
        cls,
        speech_item: TYPES.SpeechItem,
        voice_info: TTSVoiceInfo,
        language: Optional[str],
        cause: Optional[str] = None,
        parent_activity=None,
    ):
        activity = system.unstable.state_engine.start_activity(
            cause=cause,
            activity_class="tts",
            properties=(
                {
                    "text": speech_item.speech,
                    "engine": voice_info.engine,
                    **(
                        {"voice": voice_info.name}
                        if voice_info.engine != "Service Proxy"
                        else {}
                    ),
                    "backend": {
                        "name": voice_info.backend,
                        "speaker_id": voice_info.name,
                        "language": language,
                        "thinking_sound": speech_item.is_thinking,
                    },
                    "item_id": speech_item.item_id,
                    "parent_item_id": speech_item.parent_item_id,
                    "purpose": speech_item.purpose,
                }
            ),
            parent_activity=parent_activity,
        )
        tts_event = INTERACTION_HISTORY.TTSEvent(
            voice_info,
            TYPES.SpeechItem(
                speech_item.speech,
                speech_item.language_code,
                speech_item.is_thinking,
                speech_item.item_id,
                speech_item.parent_item_id,
                speech_item.purpose,
            ),
        )

        # We don't know the task id yet
        tts_client_item = TTSClientItem(tts_event)
        cls.tts_by_activity[activity] = tts_client_item

    @classmethod
    def stop(cls):
        for activity in cls.tts_by_activity.keys():
            system.unstable.state_engine.stop_activity(
                cause="TTS stop called", activity=activity
            )
        # tts_by_activity will be cleared incrementally
        # in on_tts_activity_stopped callback

    def disconnect(self):
        super().disconnect()
        try:
            import zmq
        except ImportError:
            pass
        else:
            self.events_socket.setsockopt(zmq.LINGER, 0)
        system.unstable.owner._stop_listening_to(self.events_socket)
        self.events_socket = None
        self._clear_state()
        if self._state_listeners:
            self._state_listeners.unregister()

    def on_message(self, channel, message):
        # messages are only relevant for virtual robots
        pass
