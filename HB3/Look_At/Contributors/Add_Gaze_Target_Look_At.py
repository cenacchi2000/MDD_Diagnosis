from time import time_ns as time_unix_ns

from tritium.world import World
from tritium.world.geom import Point3, Vector3

contributor = system.import_library("../../lib/contributor.py")


class Activity:
    contributor = None

    def on_start(self):
        self.contributor = contributor.Contributor(
            "look",
            "look_at_target",
            reference_frame=World.ROBOT_SPACE,
        )
        self.left_eye_converter = system.world.converter(
            "Left Eye Camera", World.ROBOT_SPACE
        )
        self.right_eye_converter = system.world.converter(
            "Right Eye Camera", World.ROBOT_SPACE
        )

        self.coords = {"x": 0, "y": 0, "z": 0}

    @system.on_event("prepare_gaze_target")
    def on_prepare_gaze_target(self, _):
        """
        Prepares the gaze target by calculating the world position of whatever the robot is currently looking at.

        Triggered when the user clicks the "Add Target" in the UI.

        NOTE: This is done separately from the actual creation of the gaze target because the robot might look away
        while the user is typing in the name.
        """

        target = Point3([1, 0, 0])

        left_eye_position = self.left_eye_converter.convert(target)

        right_eye_position = self.right_eye_converter.convert(target)

        right_vector = Vector3(
            [right_eye_position.x, right_eye_position.y, right_eye_position.z]
        )
        midpoint = (left_eye_position + right_vector) / 2

        self.coords = {"x": midpoint.x, "y": midpoint.y, "z": midpoint.z}

    @system.on_event("create_gaze_target")
    def on_create_gaze_target(self, name: str):
        """
        Creates a gaze target in the stash with the prepared coordinates and provided name.

        Triggered once the user submits a name for the gaze target being added.

        Args:
            name (str): The name of the gaze target.
        """

        system.unstable.stash.set_by_key(
            "/profile/gaze_targets",
            "name",
            name,
            {"name": name, **self.coords},
        )

    @system.on_event("look_at_gaze_target")
    def on_look_at_gaze_target(self, message: dict):
        """Handles 'look_at_gaze_target' event to direct the robot's gaze.

        Args:
            message (dict): Contains the coordinates of the gaze target.
        """
        position = Point3([message["x"], message["y"], message["z"]])

        new_look = contributor.LookAtItem(
            identifier="gaze_target",
            position=position,
            sample_time_ns=time_unix_ns(),
            distance=10,
        )
        self.contributor.update([new_look])

    @system.on_event("clear_gaze_target")
    def on_clear_gaze_target(self, _):
        """
        Stops looking at the gaze target and clears the contributor.
        """
        self.contributor.clear()

    def on_stop(self):
        self.contributor.clear()