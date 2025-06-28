from uuid import uuid4
from typing import Optional
from collections import deque

robot_state = system.import_library("../robot_state.py").state
CONFIG = system.import_library("../../Config/Chat.py").CONFIG
INTERACTION_HISTORY = system.import_library("../chat/knowledge/interaction_history.py")

TextToSpeechNodeClient = system.import_library(
    "./lib/tts_client.py"
).TextToSpeechNodeClient
TYPES = system.import_library("../lib/types.py")
stash = system.unstable.stash

tts_stop_emitter = system.world.declare_event(
    event_name="tts_interrupt", data_type=INTERACTION_HISTORY.InteractionEventData
)


class Activity:
    telepresence_started: bool = False
    client: Optional[TextToSpeechNodeClient] = None
    voices_sub = None

    def on_start(self):
        self.client = TextToSpeechNodeClient(
            system.unstable.state_engine,
            on_item_playback_started=self.on_item_playback_started,
            on_item_playback_finished=self.on_item_playback_finished,
            on_heartbeat_changed=self.on_heartbeat_changed,
        )
        self.voices_sub = stash.subscribe("/runtime/actors/text_to_speech/ttsVoices")
        self.voices_sub.add_callback(self._on_voices_updated)

        self.tts_send_queue = deque()
        self.max_active_items = 5
        self.active_item_count = 0
        self.current_activity = None

    def on_word_synch(self, tts_item_id, word_position_in_bytes, time):
        pass

    def on_bookmark(self, tts_item_id, bookmark_value, time):
        pass

    def on_item_playback_started(self, tts_item_id, tts_event, audio_start_time):
        system.messaging.post("on_tts_started", (tts_item_id, audio_start_time))
        self.add_item_to_history(tts_event)

    def on_item_playback_finished(self, tts_item_id, audio_finish_time):
        robot_state.set_currently_saying(None, probe=probe)
        self.active_item_count -= 1
        if self.active_item_count < 0:
            self.active_item_count = 0

        system.messaging.post("on_tts_finished", (tts_item_id, audio_finish_time))

    def on_heartbeat_changed(self, heartbeat):
        log.info("client heartbeat changed, resetting speech queue")
        robot_state.set_currently_saying(None, probe=probe)

    def send_client_next_item(self, tts_item):
        speech_item = tts_item

        voice_info = robot_state.get_voice_for_language(speech_item.language_code)

        if voice_info is None:
            log.error("No voice available")
            return

        if voice_info.engine == "Service Proxy":
            # Only service proxy plugin is capable of downloading multiple
            # items in parallel and playing them in order
            self.max_active_items = 5
        else:
            self.max_active_items = 1

        self.client.say(
            speech_item,
            voice_info=voice_info,
            language=speech_item.language_code,
            cause="running TTS",
        )

        self.active_item_count += 1

    def process_queue(self):
        if not self.tts_send_queue:
            return

        if self.active_item_count >= self.max_active_items:
            return

        next_item = self.tts_send_queue.popleft()
        self.send_client_next_item(next_item)

    def on_message(self, channel, message):
        if channel == "tts_say":
            if self.telepresence_started:
                return
            self.add_new_tts_item(message)
        elif channel == "telepresence":
            if message.get("type", "") == "session_active":
                self.telepresence_started = message.get("value", False)
        elif channel == "tts_stop":
            self.stop_tts(message)
        if self.client:
            self.client.on_message(channel, message)

    def add_new_tts_item(self, message):
        parent_item_id: Optional[str] = None
        if isinstance(message, dict):
            speech = message["message"]
            language_code = message["language_code"]
            is_thinking = message.get("is_thinking", False)
            parent_item_id = message.get("parent_item_id", None)
        else:
            speech, language_code = message
            is_thinking = False

        if not speech.strip() and not is_thinking:
            log.warning("Empty speech received, rejecting")
            return

        tts_item = TYPES.SpeechItem(
            speech,
            language_code,
            is_thinking,
            str(uuid4()),
            parent_item_id,
            "thinking sound" if is_thinking else None,
        )
        self.tts_send_queue.append(tts_item)
        self.process_queue()

    def reset_state(self):
        self.tts_send_queue = deque()
        self.active_item_count = 0

        robot_state.speaking = False
        robot_state.set_currently_saying(None, probe=probe)
        robot_state.cancel_response_task()

    def stop_tts(self, is_interrupt: bool):
        if is_interrupt:
            tts_stop_emitter.emit(
                INTERACTION_HISTORY.InteractionEventData(
                    "tts_interrupt", "(Robot was interrupted...)", "gray"
                )
            )

        self.client.stop()
        self.reset_state()

    def on_stop(self):
        if self.client:
            if robot_state.speaking:
                self.stop_tts(is_interrupt=False)
            self.client.disconnect()
        self.client = None
        self.voices_sub.remove_callback(self._on_voices_updated)
        self.voices_sub = None

    def add_item_to_history(self, tts_event):
        if tts_event is None:
            return

        for active_history in INTERACTION_HISTORY.InteractionHistory.get_registered(
            "TTS"
        ):
            active_history.add_to_memory(tts_event)
            log.info(f"Adding tts event to history: {tts_event}")

        robot_state.set_currently_saying(tts_event.speech_item, probe=probe)

    @system.tick(fps=5)
    def on_tick(self):
        self.process_queue()

        probe("Telepresence Started", self.telepresence_started)
        probe("Is speaking", robot_state.speaking)

        if self.telepresence_started:
            if not robot_state.speaking:
                self.client.stop()
            return

    def _on_voices_updated(self, evt) -> None:
        if evt.data is None:
            log.warning("Failed to fetch TTS voices from stash")
            robot_state.set_available_tts_voices(None)
        else:
            robot_state.set_available_tts_voices(
                [TYPES.TTSVoiceInfo(**info) for info in evt.data if info is not None]
            )

        probe(
            "TTS Voices",
            [model.name for model in robot_state.available_tts_voices or ()],
        )

        probe(
            "Default Language Voice Map",
            {
                lang: voice.name if voice else None
                for lang, voice in robot_state.default_language_voice_map.items()
            },
        )