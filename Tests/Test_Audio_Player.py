"""
Script to play test audio file

"""


class Activity:
    def on_start(self):
        self.playing_sequence = system.unstable.state_engine.start_activity(
            cause="started within script",
            activity_class="playing_audio_file",
            properties={
                "file_path": "/opt/tritium/nodes/audio_player/data/test/sound/test-sound.ogg",
                "offset": 0.0,
                "duration": 3.0,
                "loops": 1,
                "gain": 1,
                "audio_player": 1,
            },
        )
