from math import cos, sin, radians
from time import monotonic as now
from collections import namedtuple

from ea.util.number import lerp, clamp

CONFIG = system.import_library("../../Config/HB3.py").CONFIG

# N.B. HB3 MUST CONTROL EVERYTHING ON THE ROBOT CONSTANTLY
# This is so that after a sequence we reset any leftover positions.
# If changing this list make sure all major robot controls are controlled somewhere in HB3.
control_keys = [
    # Head and Neck
    ("Head Pitch", "Mesmer Neck 1"),
    ("Head Yaw", "Mesmer Neck 1"),
    ("Head Roll", "Mesmer Neck 1"),
    ("Neck Roll", "Mesmer Neck 1"),
    ("Neck Pitch", "Mesmer Neck 1"),
]
SKIP_WARMING_CONTROLS = [
    # Face Controls
    ("Eyelid Lower Left", "Mesmer Eyelids 1"),
    ("Eyelid Lower Right", "Mesmer Eyelids 1"),
    ("Eyelid Upper Left", "Mesmer Eyelids 1"),
    ("Eyelid Upper Right", "Mesmer Eyelids 1"),
    ("Nose Wrinkle", "Mesmer Nose 1"),
    ("Brow Inner Left", "Mesmer Brows 1"),
    ("Brow Outer Left", "Mesmer Brows 1"),
    ("Brow Inner Right", "Mesmer Brows 1"),
    ("Brow Outer Right", "Mesmer Brows 1"),
]

IS_GEN1_HEAD = CONFIG["ROBOT_HEAD_TYPE"] == CONFIG["ROBOT_HEAD_TYPES"].GEN1
if IS_GEN1_HEAD:
    SKIP_WARMING_CONTROLS += [
        ("Jaw Yaw", "Mesmer Mouth 1"),
        ("Jaw Open", "Mesmer Mouth 1"),
        ("Smile Left", "Mesmer Mouth 1"),
        ("Smile Right", "Mesmer Mouth 1"),
    ]
else:
    if CONFIG["ROBOT_HEAD_TYPE"] != CONFIG["ROBOT_HEAD_TYPES"].GEN2:
        raise NotImplementedError("Unknown robot head type.")
    SKIP_WARMING_CONTROLS += [
        ("Jaw Yaw", "Mesmer Mouth 2"),
        ("Mouth Anger", "Mesmer Mouth 2"),
        ("Mouth Content", "Mesmer Mouth 2"),
        ("Mouth Disgust", "Mesmer Mouth 2"),
        ("Mouth Fear", "Mesmer Mouth 2"),
        ("Mouth Happy", "Mesmer Mouth 2"),
        ("Mouth Huh", "Mesmer Mouth 2"),
        ("Mouth Joy", "Mesmer Mouth 2"),
        ("Mouth Open", "Mesmer Mouth 2"),
        ("Mouth Sad", "Mesmer Mouth 2"),
        ("Mouth Sneer", "Mesmer Mouth 2"),
        ("Mouth Surprise", "Mesmer Mouth 2"),
        ("Mouth Worried", "Mesmer Mouth 2"),
        ("Viseme A", "Mesmer Mouth 2"),
        ("Viseme CH", "Mesmer Mouth 2"),
        ("Viseme Closed", "Mesmer Mouth 2"),
        ("Viseme E", "Mesmer Mouth 2"),
        ("Viseme F", "Mesmer Mouth 2"),
        ("Viseme I", "Mesmer Mouth 2"),
        ("Viseme ING", "Mesmer Mouth 2"),
        ("Viseme KK", "Mesmer Mouth 2"),
        ("Viseme M", "Mesmer Mouth 2"),
        ("Viseme NN", "Mesmer Mouth 2"),
        ("Viseme O", "Mesmer Mouth 2"),
        ("Viseme RR", "Mesmer Mouth 2"),
        ("Viseme SS", "Mesmer Mouth 2"),
        ("Viseme U", "Mesmer Mouth 2"),
    ]


# Full body Ameca specific
IS_FULL_BODY = CONFIG["ROBOT_TYPE"] in [
    CONFIG["ROBOT_TYPES"].AMECA,
    CONFIG["ROBOT_TYPES"].AMECA_DRAWING,
]
if IS_FULL_BODY:
    control_keys += [
        # LEFT
        ("Elbow Pitch Left", "Mesmer Arms 1"),
        ("Wrist Roll Left", "Mesmer Arms 1"),
        ("Wrist Pitch Left", "Mesmer Arms 1"),
        ("Wrist Yaw Left", "Mesmer Arms 1"),
        ("Clavicle Roll Left", "Mesmer Arms 1"),
        ("Clavicle Yaw Left", "Mesmer Arms 1"),
        ("Shoulder Pitch Left", "Mesmer Arms 1"),
        ("Shoulder Roll Left", "Mesmer Arms 1"),
        ("Shoulder Yaw Left", "Mesmer Arms 1"),
        # RIGHT
        ("Elbow Pitch Right", "Mesmer Arms 1"),
        ("Wrist Roll Right", "Mesmer Arms 1"),
        ("Wrist Pitch Right", "Mesmer Arms 1"),
        ("Wrist Yaw Right", "Mesmer Arms 1"),
        ("Clavicle Yaw Right", "Mesmer Arms 1"),
        ("Shoulder Roll Right", "Mesmer Arms 1"),
        ("Clavicle Roll Right", "Mesmer Arms 1"),
        ("Shoulder Pitch Right", "Mesmer Arms 1"),
        ("Shoulder Yaw Right", "Mesmer Arms 1"),
        # Fingers
        ("Index Finger Left", "Mesmer Fingers 1"),
        ("Index Finger Right", "Mesmer Fingers 1"),
        ("Middle Finger Left", "Mesmer Fingers 1"),
        ("Middle Finger Right", "Mesmer Fingers 1"),
        ("Ring Finger Left", "Mesmer Fingers 1"),
        ("Ring Finger Right", "Mesmer Fingers 1"),
        ("Little Finger Left", "Mesmer Fingers 1"),
        ("Little Finger Right", "Mesmer Fingers 1"),
        # Torso
        ("Torso Yaw", "Mesmer Torso 1"),
        ("Torso Pitch", "Mesmer Torso 1"),
        ("Torso Roll", "Mesmer Torso 1"),
    ]

controls = {
    key: system.control(*key, acquire=["position", "min", "max", "demand"])
    for key in control_keys
}

controls.update({key: system.control(*key) for key in SKIP_WARMING_CONTROLS})


class MixDemandHub:
    Demand = namedtuple("Demand", "value relative")

    def __init__(self):
        self._contributors: dict[str, dict] = {}

        # Filters are a list of allowed identifiers and denied identifiers
        # Filters are indexed by identifier to know who set the filter (for debugging only)
        # NOTE: ALL filters are active at all times regardless of the owner of the filter.
        #   A denied contributor does not have their filter deactivated
        #   Filters must be cleared by the script responsible for them
        self._filters: dict[str, tuple[list[str], list[str]]] = {}
        self._update_filters()

    def add_relative(
        self, src_ident: str, ctrl_name: tuple[str, str], ctrl_value: float
    ):
        return self.add_demand(src_ident, ctrl_name, ctrl_value, relative=True)

    def add_absolute(
        self, src_ident: str, ctrl_name: tuple[str, str], ctrl_value: float
    ):
        return self.add_demand(src_ident, ctrl_name, ctrl_value, relative=False)

    def add_demand(
        self,
        src_ident: str,
        ctrl_name: tuple[str, str],
        ctrl_value: float,
        relative: bool = False,
    ):
        if src_ident not in self._contributors:
            self._contributors[src_ident] = {}
        self._contributors[src_ident][ctrl_name] = self.Demand(ctrl_value, relative)

    def clean(self, src_ident: str):
        self._contributors.pop(src_ident, None)

    def set_filters(
        self,
        src_ident: str,
        *,  # To prevent mixups, following lists must be passed as keyword args
        allow_list: list[str] = [],
        deny_list: list[str] = [],
    ):
        self._filters[src_ident] = (allow_list, deny_list)
        self._update_filters()

    def clear_filters(self, src_ident: str):
        self._filters.pop(src_ident, None)
        self._update_filters()

    def _update_filters(self):
        self._allow_list = [item for f in self._filters.values() for item in f[0]]
        self._deny_list = [item for f in self._filters.values() for item in f[1]]

    def get_values(self) -> dict[tuple[str, str], float]:
        vals = {}
        multi_abs = set()

        # Absolute demands first
        for source_name, dmds in self._contributors.items():
            if self._deny_list and source_name in self._deny_list:
                continue
            if self._allow_list and source_name not in self._allow_list:
                continue
            for ctrl_name, dmd in dmds.items():
                if not dmd.relative:
                    if ctrl_name in vals:
                        multi_abs.add(ctrl_name)
                    vals[ctrl_name] = dmd.value

        # Relative demands second
        for source_name, dmds in self._contributors.items():
            if self._deny_list and source_name in self._deny_list:
                continue
            if self._allow_list and source_name not in self._allow_list:
                continue
            for ctrl_name, dmd in dmds.items():
                if dmd.relative:
                    vals[ctrl_name] = vals.get(ctrl_name, 0) + dmd.value

        return vals


class Activity:
    WARM_TIME_S = 0.6  # Interpolate control if lose arbitration for a bit
    WARM_TIME_TORSO_S = 6
    MIN_SQUASH_ANGLE = 10
    HEAD_TO_NECK_PITCH_RATIO = 0.75
    HEAD_TO_NECK_ROLL_RATIO = 0.85

    def on_start(self):
        self.warming_controls = {}

        specifiers = [
            "Control/Mesmer Neck 1",
            "Control/Mesmer Brows 1",
            "Control/Mesmer Eyelids 1",
            "Control/Mesmer Nose 1",
            "Control/Mesmer Mouth 1" if IS_GEN1_HEAD else "Control/Mesmer Mouth 2",
        ]

        if IS_FULL_BODY:
            specifiers += [
                "Control/Mesmer Arms 1",
                "Control/Mesmer Torso 1",
                "Control/Mesmer Fingers 1",
            ]

        self.bid = system.arbitration.make_bid(
            specifiers=specifiers,
            precedence=Precedence.MEDIUM,
            bid_type=BidType.ON_DEMAND,
        )
        self.hub = system.unstable.owner.mix_pose = MixDemandHub()

    def avoid_collision_arms(self, values):
        # QDH: Minumum shoulder pitch up a bit to avoid colliding with the
        SHOULDER_PITCH_RIGHT_CTRL = ("Shoulder Pitch Right", "Mesmer Arms 1")
        SHOULDER_PITCH_LEFT_CTRL = ("Shoulder Pitch Left", "Mesmer Arms 1")

        values[SHOULDER_PITCH_RIGHT_CTRL] = clamp(
            values.get(SHOULDER_PITCH_RIGHT_CTRL, 0), 6, 300
        )
        values[SHOULDER_PITCH_LEFT_CTRL] = clamp(
            values.get(SHOULDER_PITCH_LEFT_CTRL, 0), 6, 300
        )

    def post_process(self, values):
        if IS_FULL_BODY:
            self.avoid_collision_arms(values)

        HEAD_YAW_CTRL = ("Head Yaw", "Mesmer Neck 1")
        HEAD_PITCH_CTRL = ("Head Pitch", "Mesmer Neck 1")
        HEAD_ROLL_CTRL = ("Head Roll", "Mesmer Neck 1")
        NECK_ROLL_CTRL = ("Neck Roll", "Mesmer Neck 1")
        NECK_PITCH_CTRL = ("Neck Pitch", "Mesmer Neck 1")

        neck_yaw = self.clamp_control(HEAD_YAW_CTRL, values.get(HEAD_YAW_CTRL, 0))
        if neck_yaw is not None:
            values[HEAD_YAW_CTRL] = neck_yaw

        ny_degrees = controls[HEAD_YAW_CTRL].position
        if ny_degrees is not None:
            ny = radians(ny_degrees)

            _head_pitch = values.get(HEAD_PITCH_CTRL, 0)
            _head_roll = values.get(HEAD_ROLL_CTRL, 0)

            # Mix pitch and roll together using the yaw to make more natural nodding
            head_pitch = cos(ny) * _head_pitch - sin(ny) * _head_roll
            head_roll = cos(ny) * _head_roll + sin(ny) * _head_pitch

            # Split across for natural usage of lower Neck
            values[NECK_PITCH_CTRL] = head_pitch * (1 - self.HEAD_TO_NECK_PITCH_RATIO)
            values[HEAD_PITCH_CTRL] = head_pitch * self.HEAD_TO_NECK_PITCH_RATIO

            values[NECK_ROLL_CTRL] = head_roll * (1 - self.HEAD_TO_NECK_ROLL_RATIO)
            values[HEAD_ROLL_CTRL] = head_roll * self.HEAD_TO_NECK_ROLL_RATIO

            # Implement imaginary Head translation controls that are useful for recoil
            neck_fwd = values.pop("Neck Forwards", 0)
            neck_left = values.pop("Neck Sideways", 0)
            roll_offset = neck_left * cos(ny) - neck_fwd * sin(ny)
            values[NECK_ROLL_CTRL] += roll_offset
            values[HEAD_ROLL_CTRL] -= roll_offset
            pitch_offset = neck_left * sin(ny) + neck_fwd * cos(ny)
            values[NECK_PITCH_CTRL] -= pitch_offset
            values[HEAD_PITCH_CTRL] += pitch_offset

            squash_angle = abs(min(0, values[HEAD_PITCH_CTRL]))
            # self.set_debug_value("squash_angle", squash_angle)
            if squash_angle > self.MIN_SQUASH_ANGLE:
                over_squash = squash_angle - self.MIN_SQUASH_ANGLE
                values[NECK_PITCH_CTRL] -= over_squash / 2
                values[HEAD_PITCH_CTRL] += over_squash / 2
        return values

    def on_stop(self):
        self.hub = None

    def control_pos(self, ctrl_name):
        pos = controls[ctrl_name].position
        assert pos is not None
        return pos

    def clamp_control(self, ctrl_name, value):
        if ctrl_name not in controls:
            return None
        min = controls[ctrl_name].min
        max = controls[ctrl_name].max
        if min is None or max is None:
            return None
        if max < min:
            min, max = max, min
        return clamp(value, min, max)

    @system.tick(fps=60)
    def on_tick(self):
        values = self.hub.get_values()

        # DEBUG
        probe("Sources", self.hub._contributors.keys())
        probe("Allowed sources", self.hub._allow_list or "All")
        probe("Denied sources", self.hub._deny_list or "None")

        for ctrl_key, value in values.items():
            if "Neck" in ctrl_key[0] or "Head" in ctrl_key[0]:
                probe(f"{ctrl_key}", value)

        # Don't send any demands if we haven't recieved the ranges
        null_ctrls = set()
        for ctrl_key, ctrl in controls.items():
            if ctrl_key not in SKIP_WARMING_CONTROLS:
                for prop in ["min", "max", "position"]:
                    if getattr(ctrl, prop, None) is None:
                        null_ctrls.add(ctrl)
        if null_ctrls:
            probe("NULL CTRLS", null_ctrls)

        values = self.post_process(values)

        t = now()
        with self.bid.use():
            for ctrl_name, value in values.items():
                if ctrl_name in SKIP_WARMING_CONTROLS:
                    ctrl = controls[ctrl_name]
                    ctrl.set_property("demand", value)
                    continue
                else:
                    try:
                        if ctrl_name is not None and value is not None:
                            if "Neck" in ctrl_name[0] or "Head" in ctrl_name[0]:
                                probe(ctrl_name, value)
                        else:
                            continue
                        # Ensure we have a WarmingControl instance for each control
                        ctrl = controls.get(ctrl_name, None)
                        if ctrl is None:
                            continue
                        wc = self.warming_controls.get(ctrl_name, None)
                        if wc:
                            position = ctrl.position
                            if position is None:
                                position = value
                            # Use the WarmingControl to decide what a sensible demand is
                            interped = wc.update(t, position, value)
                            alive = ctrl.set_property("demand", interped)
                            # Inform the WarmingControl if the demand was successful
                            wc.set_alive(alive)
                        elif wc is None:
                            alive = ctrl.set_property("demand", value)
                            wt = self.WARM_TIME_S
                            if "Torso" in ctrl_name[0]:
                                wt = self.WARM_TIME_TORSO_S
                            self.warming_controls[ctrl_name] = WarmingControl(wt, alive)
                    except KeyError:
                        pass
        warming = {n for n, wc in self.warming_controls.items() if not wc.reached}
        probe("warming", warming)


class WarmingControl:
    """
    Gradually increases the influence of a Control after we initially gain control of it
    """

    def __init__(self, warm_time, alive):
        self.warm_time = warm_time
        self.reached = True
        self.set_alive(alive)

    def set_alive(self, alive):
        self.alive = alive
        if alive is False:
            self.reached = False

    def update(self, current_time, current_position, target):
        if self.reached:
            self.position = target
            self.last_updated = current_time
            return target

        if self.alive is False:
            self.position = current_position
            self.last_updated = current_time

        t = (current_time - self.last_updated) / self.warm_time
        if t >= 1:
            self.reached = True
            self.position = target
            self.last_updated = current_time
            return target

        return lerp(self.position, target, t)