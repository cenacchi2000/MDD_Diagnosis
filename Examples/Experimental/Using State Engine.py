"""
Using State Engine

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
        # content path to an on-robot animation project
        sequence_path = "Animations.dir/Ameca.dir/Gestures.dir/Shrug.project"

        # start a sequence activity using State Engine
        self.playing_sequence = system.unstable.state_engine.start_activity(
            # causes should be provided for any changes to the state engine's activities
            cause="script started",
            # the name of the activity
            activity_class="playing_sequence",
            # properties of the activity e.g. file path
            properties={
                "file_path": f"/var/opt/tritium/content/{sequence_path}/project.json"
            },
        )

    def on_stop(self):
        # stop the sequence activity when finished
        system.unstable.state_engine.stop_activity(
            cause="script stopped", activity=self.playing_sequence
        )