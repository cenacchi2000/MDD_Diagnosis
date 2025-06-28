from math import pow, sqrt
from time import monotonic as now

from ea.util.number import lerp, clamp, remap, remap_keyframes
from ea.animation.poses import Pose

custom_types = system.import_library("../lib/types.py")

"""
A script adding proximity recoil to recognised faces.
This script will also blend the facial expression with a specified pose when user is within a specified distance.
"""

SELF_IDENTIFIER = "ADD_PROXIMITY_RECOIL"
CONFIG = system.import_library("../../Config/HB3.py").CONFIG
RECOIL_EXPRESSION = Pose(
    "discomfort",
    {
        ("Mouth Disgust", "Mesmer Mouth 2"): 0.05,
        ("Nose Wrinkle", "Mesmer Nose 1"): 0.1,
        ("Brow Inner Left", "Mesmer Brows 1"): 0.4,
        ("Brow Inner Right", "Mesmer Brows 1"): 0.4,
        ("Brow Outer Left", "Mesmer Brows 1"): 0.4,
        ("Brow Outer Right", "Mesmer Brows 1"): 0.4,
    },
)
NEUTRAL_FACE_POSE = CONFIG["NEUTRAL_FACE_POSE"]
TIMEOUT: int = 3


class Activity:
    threshold_curve = [(0, -40), (0.3, -30), (0.7, 0), (0.8, 0)]

    face_visible: bool = False

    distance_from_origin: float = float("inf")
    last: float = 0
    recoil_shadow: float = 0
    time_last_visible: float = 0

    current_face: custom_types.DetectedFace3D | None = None

    async def on_start(self):
        # Get faces from world
        async with system.world.query_features(name="faces") as sub:
            async for s in sub.async_iter():
                if s is not None:
                    self.on_face_recognise(s)

    def on_face_recognise(self, faces: list[custom_types.DetectedFace3D]):
        # Look at faces and set closest face to active face
        for face in faces:
            if face is not None:
                if (
                    self.current_face is None
                    or face.position.x < self.current_face.position.x
                ):
                    self.current_face = face

        # If face visible
        if self.current_face is not None:
            self.face_visible = True

            # Find distance using x and y values
            self.distance_from_origin = sqrt(
                pow(self.current_face.position.x, 2)
                + pow(self.current_face.position.y, 2)
            )

            # Update time a face was last visible
            self.time_last_visible = now()

            # Clear current face
            self.current_face = None
        else:
            self.face_visible = False

    def on_stop(self):
        if hasattr(system.unstable.owner, "mix_pose"):
            system.unstable.owner.mix_pose.clean(SELF_IDENTIFIER)

    @system.tick(fps=20)
    def on_tick(self):
        # If no face has been visible for over timeout
        if self.face_visible is False and (now() - self.time_last_visible) > TIMEOUT:

            # Interpolate between current position and 0
            self.recoil_shadow = lerp(self.recoil_shadow, 0, 0.3)

            # Reset head position
            if getattr(system.unstable.owner, "mix_pose", None) is not None:
                system.unstable.owner.mix_pose.add_absolute(
                    SELF_IDENTIFIER, "Neck Forwards", self.recoil_shadow
                )

            # Debug
            self.show_debug()
            return

        # Remap distance to recoil curve
        recoil = remap_keyframes(self.distance_from_origin, self.threshold_curve)

        # Set forward movement to be smoother than backwards movement
        if recoil > self.recoil_shadow:
            self.recoil_shadow = lerp(self.recoil_shadow, recoil, 0.1)
        else:
            self.recoil_shadow = lerp(self.recoil_shadow, recoil, 0.4)

        if getattr(system.unstable.owner, "mix_pose", None) is not None:
            # Move "Neck Forwards" along recoil curve
            system.unstable.owner.mix_pose.add_absolute(
                SELF_IDENTIFIER, "Neck Forwards", self.recoil_shadow
            )

            # Map and clamp expression changing range
            expression_amount = remap(self.distance_from_origin, 0.8, 0.5, 0, 1)
            expression_amount = clamp(expression_amount, 0, 1)

            # Get neutral reference expression
            neutral_expression = system.poses.get(NEUTRAL_FACE_POSE)

            # For each control variable in expression
            for ctrl, target_value in RECOIL_EXPRESSION.items():
                # Get difference between target value and neutral value
                neutral_value = neutral_expression.get(ctrl, None)
                control_value = (target_value - neutral_value) * expression_amount

                # Debug showing expected relative values
                probe(ctrl, control_value)

                # Change facial expression based on control value
                system.unstable.owner.mix_pose.add_relative(
                    SELF_IDENTIFIER, ctrl, control_value
                )

        # Debug
        self.show_debug()

    def show_debug(self):
        probe("face_visible", self.face_visible)
        probe("timeFromLastSeen", now() - self.time_last_visible)
        probe("distance", self.distance_from_origin)
        probe("recoil_amount", self.recoil_shadow)
        probe("lean_threshold", self.threshold_curve[3][0])
        probe("recoil_threshold", self.threshold_curve[1][0])