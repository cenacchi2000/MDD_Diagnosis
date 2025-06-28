"""
Logs a list of all available alternate voices supported by the robot.
They can be copied or manually filtered, and set in the persona script
"""

robot_state = system.import_library("../../HB3/robot_state.py").state


class Activity:
    def on_start(self):
        available_alternate_voices = [
            voice.__dict__
            for voice in robot_state.available_tts_voices
            if voice.backend not in ["Polly", "aws_polly_neural_v1", "espeak"]
        ]

        log.info("Available alternate voices:")
        log.info(available_alternate_voices)
        self.stop()
