"""
Play Sequence

Ensure you have a sequence project saved on the robot with an appropriate subpath
e.g. Animations.dir/Ameca.dir/Gestures.dir/Shrug.project

>>> activity = system.state_engine.start_activity(
...     "cause_of_activity",
...     "activity_name",
...     dict_of_properties e.g. file_path,
... )
>>> system.state_engine.stop_activity(
...     "cause_of_activity",
...     "activity_name",
... )
"""


class Activity:
    def on_start(self):
        self.start_playing_sequence(
            "Animations.dir/Ameca.dir/Gestures.dir/Shrug.project", "script started"
        )

    def on_stop(self):
        self.stop_playing_sequence("script stopped")

    def stop_playing_sequence(self, cause):
        system.unstable.state_engine.stop_activity(
            cause=cause, activity=self.playing_sequence
        )

    def start_playing_sequence(self, path, cause):
        self.playing_sequence = system.unstable.state_engine.start_activity(
            cause=cause,
            activity_class="playing_sequence",
            properties={"file_path": f"/var/opt/tritium/content/{path}"},
        )
