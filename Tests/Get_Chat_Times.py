"""
Add a short description of your script here
"""

from time import monotonic as time

VAD = system.import_library("../HB3/Perception/VAD_subscription.py").VAD
AUDIO_SOURCES = ["service_proxy"]
AUDIO_LEVELS = system.control("Audio Levels", None, acquire=AUDIO_SOURCES)


class Activity:
    debug_start: float = 0
    user_speech_start_time: float = 0
    user_speech_end_time: float = 0
    asr_start_time: float = 0
    asr_finish_time: float = 0
    llm_start_time: float = 0
    llm_end_time: float = 0
    tts_start_time: float = 0
    in_sequence: bool = False
    talk_time: float = 0
    talk_to_asr_time: float = 0
    asr_time: float = 0
    llm_time: float = 0
    remaining_time: float = 0
    llm_finished = False
    output = {}

    async def on_start(self):
        # Subscribe to Voice Activiity Detection (VAD)
        VAD.executed_functions.handle(self.check_VAD_change)
        self.vad = False

        # Iterate through responses from Speech Recognition Node
        async with system.world.query_features(name="speech_recognition") as sub_asr:
            async for sub in sub_asr.async_iter():
                match sub.type:
                    case "speech_started":
                        # Lock start time until a full run is complete
                        if self.in_sequence is False:
                            # Get time when user starts speaking
                            self.user_speech_start_time = time()

                            print("start_speech", self.user_speech_start_time)
                            probe("start_speech", self.user_speech_start_time)
                    case "speech_stopped":
                        # Get time when ASR starts/when the speech recogniser stops listening
                        self.asr_start_time = time()
                        # Calculate time between speech end and stop listening
                        self.talk_to_asr_time = (
                            self.asr_start_time - self.user_speech_end_time
                        )

                        probe("asr_start_time", self.talk_to_asr_time)
                        probe("ASR Start", self.asr_start_time)
                    case "speech_recognized":
                        # Get time when speech has been processed
                        self.asr_finish_time = time()
                        self.in_sequence = True

                        # Reset times output
                        self.output = {}

                        # Sets the start time when speech has been recognised
                        self.debug_start = self.user_speech_start_time
                        probe("start_ref", self.debug_start)

                        # Calculate time user was talking for
                        self.talk_time: float = (
                            self.user_speech_end_time - self.debug_start
                        )
                        probe("Talk time", self.talk_time)

                        # Calculate the amount of time taken for ASR to work
                        self.asr_time: float = (
                            self.asr_finish_time - self.asr_start_time
                        )

                        probe("ASR Time", self.asr_time)
                        probe("ASR End Time", self.asr_finish_time)

                        # Debug
                        print(
                            f"ASR Time: {self.asr_time} = {self.asr_finish_time} - {self.user_speech_end_time}"
                        )
                        print(self.asr_finish_time, sub.type, sub.text)
                        print("ASR Time", self.asr_time)

                        # Update output
                        self.output.update({"Talk Time": self.talk_time})
                        self.output.update({"Talk To ASR Time": self.talk_to_asr_time})

    def check_VAD_change(self, data: dict):
        # If theres been a change in VAD
        if self.vad is not None:
            if data["detected"] is False and self.vad:  # and in_sequence:
                self.user_speech_end_time = time()
                print("end_speech", self.user_speech_end_time)
                probe("end_speech", self.user_speech_end_time)  # self.look_at()

        self.vad = data["detected"]

    def on_message(self, channel, message):
        match channel:
            case "speech_recognized":
                # Get time when LLM starts
                self.llm_start_time = time()

                probe("LLM Start", self.llm_start_time)
                print("LLM Start", self.llm_start_time)
            case "llm_finished":
                # Get time when LLM ends
                self.llm_end_time = time()

                probe("LLM End", self.llm_end_time)
                print("LLM End", self.llm_end_time)

                # Calculate time taken for LLM call to run
                self.llm_time = self.llm_end_time - self.llm_start_time

                probe("LLM Time", self.llm_time)
                print("LLM Time", self.llm_time)

                # Update output
                self.output.update({"LLM Time": self.llm_time})
                self.llm_finished = True

    def get_max_audio_source(self):
        max_val = 0
        max_val_source = None
        for audio_source in AUDIO_SOURCES:
            val = getattr(AUDIO_LEVELS, audio_source)
            probe(audio_source, val)
            if val is not None and val > max_val:
                max_val = val
                max_val_source = audio_source
        return max_val, max_val_source

    @system.tick(fps=20)
    def on_tick(self):
        # Debug
        probe("In Progress", self.in_sequence)
        probe("LLM finished", self.in_sequence)

        # Get tts output volume
        audio_value, audio_source = self.get_max_audio_source()
        probe(audio_source, audio_value)

        # When Ameca starts responding
        if audio_value > 0 and self.in_sequence and self.llm_finished:
            # Get time of Ameca starting to talk
            self.tts_start_time = time()

            # Calculate the time between llm end and tts start
            self.remaining_time = self.tts_start_time - self.llm_end_time

            # Calculate the time between ASR ending and LLM starting
            asr_llm_time = self.llm_start_time - self.asr_finish_time

            # Debug
            print(
                f"End Time: {self.remaining_time} = {self.tts_start_time} - {self.llm_end_time}"
            )
            probe("LLM to TTS Time", self.remaining_time)
            probe("ASR to LLM Time", asr_llm_time)
            probe("TTS Start", self.tts_start_time)
            print("TTS Start", self.tts_start_time)

            # Update output
            self.output.update({"LLM to TTS": self.remaining_time})
            self.output.update({"ASR Time": self.asr_time - asr_llm_time})
            self.output.update({"ASR to LLM": abs(asr_llm_time)})

            # Calculate the overall time by checking end time against start time
            overall_time = self.tts_start_time - self.debug_start
            probe("Overall Time", overall_time)

            # Update output
            self.output.update({"Overall Time": overall_time})

            # Calculate overall time by adding up all
            added_time = (
                self.talk_time
                + self.talk_to_asr_time
                + self.asr_time
                + asr_llm_time
                + self.llm_time
                + self.remaining_time
            )
            print(
                f"{added_time} = {self.talk_time} + {self.talk_to_asr_time} + {self.asr_time} + {asr_llm_time} + {self.llm_time} + {self.remaining_time}"
            )
            probe("Added Time", added_time)

            # Reset loop
            self.in_sequence = False
            self.llm_finished = False

            # Output
            print("CHAT_TIMES,", self.output)