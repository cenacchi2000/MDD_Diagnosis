import random

from ea.animation.poses import Pose

contributor = system.import_library("../lib/contributor.py")

SELF_IDENTIFIER = "ADD_FACE_NEUTRAL"

CONFIG = system.import_library("../../Config/HB3.py").CONFIG

NEUTRAL_FACE_POSE = CONFIG["NEUTRAL_FACE_POSE"]

EXPRESSIONS = [
    # Blank one for neutral
    Pose("no change", {}),
    Pose(
        "disgust",
        {
            ("Mouth Disgust", "Mesmer Mouth 2"): 0.2,
        },
    ),
    Pose(
        "happy",
        {
            ("Mouth Happy", "Mesmer Mouth 2"): 0.1,
            ("Brow Inner Left", "Mesmer Brows 1"): 0.8,
            ("Brow Inner Right", "Mesmer Brows 1"): 0.8,
            ("Brow Outer Left", "Mesmer Brows 1"): 0.8,
            ("Brow Outer Right", "Mesmer Brows 1"): 0.8,
        },
    ),
    Pose(
        "huh",
        {
            ("Mouth Huh", "Mesmer Mouth 2"): 0.24,
        },
    ),
    Pose(
        "sneer",
        {
            ("Mouth Sneer", "Mesmer Mouth 2"): 0.2,
        },
    ),
    Pose(
        "sneer brows 1",
        {
            ("Mouth Surprise", "Mesmer Mouth 2"): 0.07,
            ("Brow Inner Left", "Mesmer Brows 1"): 0.4,
            ("Brow Inner Right", "Mesmer Brows 1"): 0.4,
        },
    ),
    Pose(
        "sneer brows 2",
        {
            ("Mouth Surprise", "Mesmer Mouth 2"): 0.07,
            ("Brow Inner Left", "Mesmer Brows 1"): 0.3,
            ("Brow Inner Right", "Mesmer Brows 1"): 0.3,
        },
    ),
    Pose(
        "content",
        {
            ("Mouth Content", "Mesmer Mouth 2"): 1,
            ("Brow Outer Left", "Mesmer Brows 1"): 0.8,
            ("Brow Outer Right", "Mesmer Brows 1"): 0.8,
        },
    ),
]

MICRO_EXPRESSION_CONTROLS = {
    # These are fed into random.triangular
    ("Mouth Happy", "Mesmer Mouth 2"): (0, 0.04, 0),
    ("Mouth Huh", "Mesmer Mouth 2"): (0, 0.1, 0.01),
    ("Mouth Sneer", "Mesmer Mouth 2"): (0, 0.03, 0),
    ("Mouth Surprise", "Mesmer Mouth 2"): (0, 0.07, 0.01),
    ("Mouth Content", "Mesmer Mouth 2"): (0, 1, 0.05),
    ("Brow Inner Left", "Mesmer Brows 1"): (-0.2, 0.2, 0),
    ("Brow Inner Right", "Mesmer Brows 1"): (-0.2, 0.2, 0),
    ("Brow Outer Left", "Mesmer Brows 1"): (-0.2, 0.2, 0),
    ("Brow Outer Right", "Mesmer Brows 1"): (-0.2, 0.2, 0),
    ("Nose Wrinkle", "Mesmer Nose 1"): (0, 0.3, 0.1),
}


# The higher this number the fewer frames will change the current micro-expression
# 0 -> 1
MICRO_EXPRESSION_STABILITY = 0.9


# The higher this number the fewer new look-at items will change the current expression
# 0 -> 1
EXPRESSION_STABILITY = 0.3

# The higher this number the slower changes to expressions will be interpolated to
# 0 -> 1
EXPRESSION_CHANGE_RATE = 0.5


class Activity:
    """
    Applies the configured Natural pose of the robot as a baseline for other procedural
    animation to be mixed on top of.
    """

    consumer = None

    def on_start(self):
        self.consumer = contributor.ConsumerRef("look")
        self.current_pose = system.poses.get(NEUTRAL_FACE_POSE).clone()
        self.target_pose = self.current_pose
        self.micro_pose = {}
        self.apply_pose()

    def on_stop(self):
        if hasattr(system.unstable.owner, "mix_pose"):
            system.unstable.owner.mix_pose.clean(SELF_IDENTIFIER)

    def apply_pose(self):
        if not hasattr(system.unstable.owner, "mix_pose"):
            return

        # Apply the current single-frame micro-expression to the target expression
        tgt = self.target_pose.clone()
        for c, v in self.micro_pose.items():
            tgt[c] = tgt.get(c, 0) + v

        # Debug info for micro expressions
        micro_sum = sum(abs(v) for v in self.micro_pose.values())
        probe("micro influence sum", micro_sum)
        probe(
            "micro influence max",
            max(self.micro_pose.items(), key=lambda x: x[1], default=None),
        )
        probe(
            "micro influence mean",
            micro_sum / len(self.micro_pose) if self.micro_pose else None,
        )

        # Interpolate towards the current target expression
        # This just adds a bit of subtle smoothing to the entire expression stuff
        pose = tgt.interpolate(self.current_pose, EXPRESSION_CHANGE_RATE, sparse=True)

        # Apply to mix_pose and store
        for ctrl, value in pose.items():
            probe(ctrl, value)
            self.current_pose[ctrl] = value
            system.unstable.owner.mix_pose.add_absolute(
                SELF_IDENTIFIER, ctrl, value + random.random() * 0.01
            )

    def on_message(self, channel, message):
        if self.consumer:
            self.consumer.on_message(channel, message)

    _last_active = 0

    @system.tick(fps=15)  # All *STABILITY settings will be affected by this rate
    def on_tick(self):
        c = self.consumer.object()
        # avoid glances causing expression resets
        if c and not (c.active and c.active.config.name == "glance"):
            is_new_target = self._last_active != c.active_changed_at
            self._last_active = c.active_changed_at
            # If we are looking at a new thing, we have a random chance to
            # choose a new expression.
            if is_new_target and random.random() > EXPRESSION_STABILITY:
                expr = random.choice(EXPRESSIONS)
                probe("expr", expr.name)
                # Grab neutral and apply chosen expression
                neutral = system.poses.get(NEUTRAL_FACE_POSE)
                self.target_pose = expr.combined(neutral)

        # Every single frame we consider changing face micro-expression
        if random.random() > MICRO_EXPRESSION_STABILITY:
            self.micro_pose = {
                c: random.triangular(*g) for c, g in MICRO_EXPRESSION_CONTROLS.items()
            }
        self.apply_pose()