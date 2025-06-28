"""
Say Text To Speech

Ensure you have a Text To Speech node installed and running
"""


class Activity:
    playing = None

    def on_start(self):
        self.say("Testing Testing 1 2 3", "example script")

    def on_stop(self):
        self.stop_saying("script stopped")

    def stop_saying(self, cause):
        if self.playing:
            system.unstable.state_engine.stop_activity(
                cause=cause, activity=self.playing
            )

    def say(self, text, cause):
        self.playing = system.unstable.state_engine.start_activity(
            cause=cause,
            activity_class="tts",
            properties={"text": text, "engine": "espeak"},
        )
