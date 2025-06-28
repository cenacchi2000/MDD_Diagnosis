import math
from time import monotonic
from itertools import count
from collections import defaultdict

from tritium.world.geom import Point3

id_counter = count()

MATCHING_FACE_ANGLE = 20
MATCHING_FACE_COSINE_THRESH = math.cos(math.radians(MATCHING_FACE_ANGLE))

perception_state = system.import_library("./perception_state.py").perception_state
TYPES = system.import_library("../lib/types.py")
microphone = system.control(
    "Microphone Array", None, acquire=["direction", "voice_activity"]
)


MYSTERY_SPEAKER_HEIGHT = 1.8
MYSTERY_SPEECH_LIFETIME_S = 5
speech_publisher = system.world.publish(
    "mystery_speakers", TYPES.SpeechBubble, display="speak"
)


class Activity:
    _person_speaking: bool = False
    _doa_bin: defaultdict[int, int] = defaultdict(lambda: 0)
    _speaker_votes = defaultdict(lambda: 0)
    _mystery_speakers: list[float, TYPES.SpeechBubble] = []

    def on_start(self):
        self._person_speaking = False
        self._doa_bin.clear()
        self._speaker_votes.clear()
        self._mystery_speakers = []

    def on_message(self, channel, message):
        match channel:
            case "speech_heard" | "no_speech_heard":
                self._person_speaking = False
                for face in perception_state.world_faces:
                    if face.said == "...":
                        face.said = None
            case "speech_recognized":
                self._person_speaking = False
                if self._speaker_votes:
                    speaker = max(
                        self._speaker_votes.items(),
                        key=lambda item: item[1],
                    )[0]
                    if speaker in perception_state.world_faces:
                        speaker.said = message["text"]
                        return
                if mystery_speaker_location := self.get_mystery_speaker_position():
                    mystery_speaker_timeout = monotonic() + MYSTERY_SPEECH_LIFETIME_S
                    self._mystery_speakers.append(
                        (
                            mystery_speaker_timeout,
                            TYPES.SpeechBubble(
                                message["text"],
                                mystery_speaker_location,
                                next(id_counter),
                            ),
                        )
                    )
            case "speech_started":
                self._speaker_votes.clear()
                self._person_speaking = True

    @system.watch(microphone)
    def on_change(self, changed):
        if microphone.voice_activity and microphone.direction is not None:
            doa = 90 - microphone.direction
            self._doa_bin[doa] += 1
        elif not self._person_speaking:
            self._doa_bin.clear()

    def get_speaker(self):
        # Just take the mode of the doa's for now
        # The speaker seems to hear itself / it's motors at position of 0 doa. We just drop this
        doas_sans_0 = {
            doa: occurrences
            for doa, occurrences in self._doa_bin.items()
            if not doa == 0
        }
        if not doas_sans_0:
            return None
        mode_doa = max(
            doas_sans_0.items(),
            key=lambda item: item[1],
        )[0]
        best_possible_match = None
        for face in perception_state.world_faces:
            face_angle = math.degrees(math.atan2(face.position.y, face.position.x))
            distance = abs(face_angle - mode_doa)
            if distance < MATCHING_FACE_ANGLE:
                if not best_possible_match or distance < best_possible_match[0]:
                    best_possible_match = (distance, face)
        if best_possible_match:
            return best_possible_match[1]
        else:
            return None

    @system.tick(fps=4)
    def on_tick(self):
        if self._person_speaking:
            if speaker := self.get_speaker():
                self._speaker_votes[speaker] += 1

                if not speaker.said:
                    speaker.said = "..."

        time_now = monotonic()

        # Timeout mystery speakers
        self._mystery_speakers = [
            (timeout, speech_item)
            for timeout, speech_item in self._mystery_speakers
            if time_now < timeout
        ]

        # Publish mystery speakers
        speech_publisher.write(
            [speech_item for _, speech_item in self._mystery_speakers]
        )

    def get_mystery_speaker_position(self):
        doas_sans_0 = {
            doa: occurrences
            for doa, occurrences in self._doa_bin.items()
            if not doa == 0
        }
        if not doas_sans_0:
            return None
        mode_doa = max(
            doas_sans_0.items(),
            key=lambda item: item[1],
        )[0]

        return Point3(
            [
                math.cos(math.radians(mode_doa)),
                math.sin(math.radians(mode_doa)),
                MYSTERY_SPEAKER_HEIGHT,
            ]
        )