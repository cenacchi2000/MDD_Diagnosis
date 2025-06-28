import os
from typing import List, Optional
from collections import deque

CONFIG = system.import_library("../../Config/Static.py")
MAX_QUEUED_SEQUENCES = 20


class Activity:
    playing_sequence: Optional["Activity"] = None

    def on_start(self):
        self.buffer: deque = deque(maxlen=MAX_QUEUED_SEQUENCES)

    def on_message(self, channel: str, message: str):
        if channel == "play_sequence":
            self.buffer.append(message)
        elif channel == "stop_sequence":
            self.stop_sequence(*message)
        elif channel == "stop_all_sequences":
            self.buffer.clear()
            self.stop_all_sequences()

    def play_sequence(self, sequence_identifier: str):
        path = CONFIG.BASE_CONTENT_PATH + sequence_identifier
        if not os.path.isdir(path):
            print(
                f'Unable to to find "{sequence_identifier}" from in base sequence dir'
            )
            return

        old_playing_sequence = self.playing_sequence
        print("PLAYING", sequence_identifier)
        self.playing_sequence = system.unstable.state_engine.start_activity(
            cause="Do_Sequence.py",
            activity_class="playing_sequence",
            properties={"file_path": f"{path}"},
        )
        if old_playing_sequence and not old_playing_sequence.stopped:
            self.stop_sequence()

    def stop_sequence(self, *sequence_to_stop: List[str]):
        for activity in system.unstable.state_engine._state.activities:
            for sequence in sequence_to_stop:
                if activity.properties is None:
                    continue
                file_path = activity.properties.get("file_path", None)
                if file_path is not None and sequence in file_path:
                    system.unstable.state_engine.stop_activity(
                        "Stopping sequence", activity
                    )

    def stop_all_sequences(self):
        system.unstable.state_engine.stop_activity(
            cause="Change emotion",
            activity=self.playing_sequence,
        )

    @system.tick(fps=5)
    def on_tick(self):
        if not self.buffer:
            return

        first_request: bool = self.playing_sequence is None
        sequence_done: bool = self.playing_sequence and self.playing_sequence.stopped
        if first_request or sequence_done:
            sequence_identifier: str = self.buffer.pop()
            self.play_sequence(sequence_identifier)