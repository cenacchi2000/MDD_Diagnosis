from typing import Any

import tritium.state_engine.client.events as state_engine_events

CONFIG = system.import_library("../../Config/Chat.py").CONFIG
CONFIG_UTILS = system.import_library("../../Config/utils.py")
DISABLE_ASR_WHILE_SPEAKING = CONFIG["DISABLE_ASR_WHILE_SPEAKING"]
SpeechRecognitionClient = system.import_library(
    "./lib/asr_client.py"
).SpeechRecognitionClient
VOICE_ID_UTIL = system.import_library("./lib/voice_id_util.py")

ROBOT_STATE = system.import_library("../robot_state.py")
robot_state = ROBOT_STATE.state

PAUSE_WORTHY_ACTIVITY_IDENTIFIERS = [
    "playing_audio_file",
    "tts",
]


class Activity:
    _talking = False
    _processing_speech = False
    _asr_enabled = True

    def on_start(self):
        self.client = SpeechRecognitionClient(system.unstable.owner)
        self.client.start_speech_recognition()
        self.sub = system.world.query_features(name="speech_recognition")
        self.speech = ""
        self.last_send_speech_time_stamp = 0
        self._state_listeners = []

        if DISABLE_ASR_WHILE_SPEAKING:
            events = [
                state_engine_events.ActivityStarted,
                state_engine_events.ActivityStopped,
                state_engine_events.ActivityInhibited,
                state_engine_events.ActivityResumed,
                state_engine_events.ActivityPaused,
                state_engine_events.ActivityDestroyed,
            ]
            self._playing = set()

            for e in events:
                for ai in PAUSE_WORTHY_ACTIVITY_IDENTIFIERS:
                    self._state_listeners.append(
                        system.unstable.state_engine.add_event_listener(
                            self.on_state_engine_updated, ai, e
                        )
                    )
            self.on_state_engine_updated()

    def on_stop(self):
        self.client.stop_speech_recognition()
        self.client.disconnect()
        self.client = None
        for listener in self._state_listeners:
            system.unstable.state_engine.remove_event_listener(listener)

        self.sub.close()

    @system.on_event("disable_asr_while_speaking")
    def on_disable_asr(self, message):
        global DISABLE_ASR_WHILE_SPEAKING
        DISABLE_ASR_WHILE_SPEAKING = message

    @system.on_event("enable_manual_mode")
    def on_enable_manual_mode(self, message):
        self.client.activate_manual_mode()

    @system.on_event("disable_manual_mode")
    def on_disable_manual_mode(self, message):
        self.client.deactivate_manual_mode()

    @system.on_event("manual_mode_stop_listening")
    def on_stop_listening(self, message):
        self.client.manual_mode_stop_listening()

    async def on_message(self, channel, msg):
        if channel == "processing_speech":
            self._processing_speech = msg

        if DISABLE_ASR_WHILE_SPEAKING:
            new_asr_enabled = (not robot_state.speaking) and (
                not self._processing_speech
            )

            if new_asr_enabled != self._asr_enabled:
                self._asr_enabled = new_asr_enabled
                log.info(f"ASR_ENABLE: {self._asr_enabled}")
                if self._asr_enabled:
                    self.client.start_speech_recognition()
                    if self._playing:
                        self.client.pause_speech_recognition()
                    else:
                        self.client.resume_speech_recognition()
                else:
                    self.client.pause_speech_recognition()

        await self.client.on_message(channel, msg)

        probe("ASR Enabled", self.client.asr_enabled)
        probe("ASR Paused", self.client.asr_paused)

    def send_on_speech_recognition_recognized(
        self, event: dict[str, Any], timestamp: float
    ):
        if self.last_send_speech_time_stamp != timestamp:
            # Deal with whisper's hallucinations
            if not CONFIG_UTILS.clean_phrase(event["text"]) in CONFIG["IGNORE_PHRASES"]:
                if metadata := event.get("metadata"):
                    if voice_ids := getattr(metadata, "voice_ids", None):
                        if speaker_name := VOICE_ID_UTIL.process_voice_id(voice_ids):
                            event["speaker"] = speaker_name

                system.messaging.post("speech_recognized", event)
        self.last_send_speech_time_stamp = timestamp

    def on_state_engine_updated(self, *args, **kwargs):
        playing = set()
        for a in system.unstable.state_engine._state.activities:
            if a.activity_class.identifier in PAUSE_WORTHY_ACTIVITY_IDENTIFIERS:
                playing.add(a.id)

        if playing and not self._playing:
            self.client.pause_speech_recognition()
        if self._playing and not playing:
            self.client.resume_speech_recognition()
        self._playing = playing
        probe("activities", playing)

        probe("ASR Enabled", self.client.asr_enabled)
        probe("ASR Paused", self.client.asr_paused)

    @system.tick(fps=2)
    async def on_tick(self):
        async for evt in self.sub.async_iter():
            time_s = evt.timestamp
            probe("evt", evt)
            probe("ASR Enabled", self.client.asr_enabled)
            probe("ASR Paused", self.client.asr_paused)
            match evt.type:
                case "speech_recognized":
                    self.send_on_speech_recognition_recognized(evt.__dict__, time_s)
                    probe("speech", evt.text)
                case "speech_started":
                    system.messaging.post("speech_started", None)
                case "speech_heard":
                    system.messaging.post("speech_heard", evt.text)
                case "no_speech_heard":
                    system.messaging.post("no_speech_heard", None)