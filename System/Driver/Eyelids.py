from time import monotonic as now

from ea.animation import INTERP_LINEAR
from ea.util.number import clamp, remap
from ea.animation.structural import Clip

robot_state = system.import_library("../../HB3/robot_state.py").state

eye_pitch_control = system.control(
    "Eye Pitch Right", "Mesmer Eyes 1", acquire=["demand"]
)

eyelid_upper_right_control = system.control(
    "Eyelid Upper Right", None, acquire=["position"]
)
eyelid_upper_left_control = system.control(
    "Eyelid Upper Left", None, acquire=["position"]
)
eyelid_lower_right_control = system.control(
    "Eyelid Lower Right", None, acquire=["position"]
)
eyelid_lower_left_control = system.control(
    "Eyelid Lower Left", None, acquire=["position"]
)

# eye openness
SQUEEZED_CLOSED = -1
NORMAL_CLOSED = 0
NORMAL_OPEN = 1
WIDE_OPEN = 2


@device(name="Human Behaviour - Eyelids")
class Activity:
    _upper_follow_gain = 1
    _lower_follow_gain = 0.8
    IDLE_THRESH = 2

    _last_eye_pitch = None
    last_blink_time = now()
    blink_time_out = 0.5  # Seconds

    @parameter(
        "float", name="Follow Gain.Upper", min_value=0, max_value=2, persistent=True
    )
    def upper_follow_gain(self):
        return self._upper_follow_gain

    @upper_follow_gain.setter
    def set_upper_follow_gain(self, value):
        self._upper_follow_gain = value

    @upper_follow_gain.on_demand
    def on_demand_upper_follow_gain(self, value):
        self.set_upper_follow_gain(value)

    @parameter(
        "float", name="Follow Gain.Lower", min_value=0, max_value=2, persistent=True
    )
    def lower_follow_gain(self):
        return self._lower_follow_gain

    @lower_follow_gain.setter
    def set_lower_follow_gain(self, value):
        self._lower_follow_gain = value

    @lower_follow_gain.on_demand
    def on_demand_lower_follow_gain(self, value):
        self.set_lower_follow_gain(value)

    ##########################################################################

    eyelid_upper_right = None
    eyelid_upper_left = None
    eyelid_lower_right = None
    eyelid_lower_left = None
    _last_demand = now()

    def on_start(self):
        self.bid = system.arbitration.make_bid(
            specifiers=["Control/Direct Motors/Eyelid Motors"],
            # Needs to be higher than sequences. Almost all control will go through this.
            precedence=Precedence.VERY_HIGH,
            bid_type=BidType.ON_DEMAND,
        )

        self.eyelid_upper_right = Eyelid(eyelid_upper_right_control, self.bid)
        self.eyelid_upper_left = Eyelid(eyelid_upper_left_control, self.bid)
        self.eyelid_lower_right = Eyelid(eyelid_lower_right_control, self.bid)
        self.eyelid_lower_left = Eyelid(eyelid_lower_left_control, self.bid)

        self.set_upper_right_openness(NORMAL_OPEN)
        self.set_upper_left_openness(NORMAL_OPEN)
        self.set_lower_right_openness(NORMAL_OPEN)
        self.set_lower_left_openness(NORMAL_OPEN)

        self.watcher(
            [
                eyelid_upper_right_control,
                eyelid_upper_left_control,
                eyelid_lower_right_control,
                eyelid_lower_left_control,
            ]
        )

    @property
    def lids(self):
        yield self.eyelid_upper_right
        yield self.eyelid_upper_left
        yield self.eyelid_lower_right
        yield self.eyelid_lower_left

    @property
    def upper_lids(self):
        yield self.eyelid_upper_right
        yield self.eyelid_upper_left

    @property
    def lower_lids(self):
        yield self.eyelid_lower_right
        yield self.eyelid_lower_left

    @system.on_event("human-behaviour-blink")
    def on_blink(self, message: dict):
        duration = message.get("duration")
        close_left = message.get("close_left")
        close_right = message.get("close_right")
        self.blink(duration, close_left, close_right)

    def blink(self, duration, close_left=None, close_right=None):
        # print("BLINK", duration)

        if close_left is None:
            close_left = 1

        if close_right is None:
            close_right = close_left

        until = now() + duration

        if close_left:
            if self.eyelid_upper_left:
                self.eyelid_upper_left.blink(until, 1 - close_left)
            if self.eyelid_lower_left:
                self.eyelid_lower_left.blink(until, 1 - close_left)

        if close_right:
            if self.eyelid_upper_right:
                self.eyelid_upper_right.blink(until, 1 - close_right)
            if self.eyelid_lower_right:
                self.eyelid_lower_right.blink(until, 1 - close_right)

        self._update_pose()

    def set_pose(self, tl, tr, bl, br):
        if tl is not None and self.eyelid_upper_left:
            self.eyelid_upper_left.openness = tl
        if tr is not None and self.eyelid_upper_right:
            self.eyelid_upper_right.openness = tr
        if bl is not None and self.eyelid_lower_left:
            self.eyelid_lower_left.openness = bl
        if br is not None and self.eyelid_lower_right:
            self.eyelid_lower_right.openness = br

    def _update_pose(self):
        t = now()
        for lid in self.lids:
            lid.maybe_unblink(t)

        eye_pitch = eye_pitch_control.demand
        if eye_pitch is not None:
            eye_pitch = round(eye_pitch, 2)
        probe("eye pitch", eye_pitch)

        force = self._last_eye_pitch != eye_pitch
        probe("force", force)
        self._last_eye_pitch = eye_pitch

        if force or any(lid.dirty for lid in self.lids):
            self._pose_eyelids(force, eye_pitch)

        # This lets us know that images take will not be affected by blinking or eyelid movement
        if any(lid.blinking for lid in self.lids):
            self.last_blink_time = t
            robot_state.blinking = True
        else:
            if t > self.last_blink_time + self.blink_time_out:
                robot_state.blinking = False

    def _pose_eyelids(self, force, eye_pitch):
        clip = self._make_eyelid_clip(eye_pitch)

        for lid in self.lids:
            lid.update_from_clip(clip, force)

    def _make_eyelid_clip(self, eye_pitch):
        # TODO: cache
        wide, opun, close, squeeze = self._calc_eyelid_poses(eye_pitch)
        clip = Clip({}, [])
        if squeeze:
            clip.add_pose(squeeze, -1, INTERP_LINEAR)
        if close:
            clip.add_pose(close, 0, INTERP_LINEAR)
        if opun:
            clip.add_pose(opun, 1, INTERP_LINEAR)
        if wide:
            clip.add_pose(wide, 2, INTERP_LINEAR)
        return clip

    def _calc_feedback(self, eye_pitch, position, lid):
        # TODO: cache
        wide, opun, close, squeeze = self._calc_eyelid_poses(None)
        cp = lid.control_pair

        if (wide[cp] if wide else opun[cp]) > (squeeze[cp] if squeeze else close[cp]):
            if position >= opun[cp]:
                return remap(position, opun[cp], wide[cp], 1, 2, clamp=True)
            if position >= close[cp]:
                return remap(position, close[cp], opun[cp], 0, 1, clamp=True)
            if position >= squeeze[cp]:
                return remap(position, squeeze[cp], close[cp], -1, 0, clamp=True)
            return -1
        else:
            if position >= close[cp]:
                return remap(position, squeeze[cp], close[cp], -1, 0, clamp=True)
            if position >= opun[cp]:
                return remap(position, close[cp], opun[cp], 0, 1, clamp=True)
            if position >= wide[cp]:
                return remap(position, opun[cp], wide[cp], 1, 2, clamp=True)
            return 2

    def _calc_eyelid_poses(self, eye_pitch):
        wide = system.poses.get("eyelids_wide")  # 2
        opun = system.poses.get("eyelids_open")  # 1
        close = system.poses.get("eyelids_close")  # 0
        squeeze = system.poses.get("eyelids_squeeze")  # -1

        if eye_pitch is not None:
            upper_offset = -eye_pitch * self._upper_follow_gain
            lower_offset = -eye_pitch * self._lower_follow_gain

            # Before mutating, copy...
            if wide is not None:
                wide = wide.clone()
                for lid in self.upper_lids:
                    wide[lid.control_pair] += upper_offset
                for lid in self.lower_lids:
                    wide[lid.control_pair] -= lower_offset

            if opun is not None:
                opun = opun.clone()
                for lid in self.upper_lids:
                    opun[lid.control_pair] += upper_offset
                for lid in self.lower_lids:
                    opun[lid.control_pair] -= lower_offset

        return wide, opun, close, squeeze

    @system.tick(fps=60)
    def on_tick(self):
        if now() - self._last_demand > self.IDLE_THRESH:
            self.set_upper_right_openness(NORMAL_OPEN)
            self.set_upper_left_openness(NORMAL_OPEN)
            self.set_lower_right_openness(NORMAL_OPEN)
            self.set_lower_left_openness(NORMAL_OPEN)
        self._update_pose()

    @system.watch(
        [
            eyelid_upper_right_control,
            eyelid_upper_left_control,
            eyelid_lower_right_control,
            eyelid_lower_left_control,
        ]
    )
    def watcher(self, changed, *args):
        eye = eye_pitch_control.demand
        if eyelid_upper_right_control in changed:
            p = eyelid_upper_right_control.position
            if p is not None:
                p = self._calc_feedback(eye, p, self.eyelid_upper_right)
                self.set_upper_right_openness_feedback(p)

        if eyelid_upper_left_control in changed:
            p = eyelid_upper_left_control.position
            if p is not None:
                p = self._calc_feedback(eye, p, self.eyelid_upper_left)
                self.set_upper_left_openness_feedback(p)

        if eyelid_lower_right_control in changed:
            p = eyelid_lower_right_control.position
            if p is not None:
                p = self._calc_feedback(eye, p, self.eyelid_lower_right)
                self.set_lower_right_openness_feedback(p)

        if eyelid_lower_left_control in changed:
            p = eyelid_lower_left_control.position
            if p is not None:
                p = self._calc_feedback(eye, p, self.eyelid_lower_left)
                self.set_lower_left_openness_feedback(p)

    ##########################################################################

    @parameter(
        "float",
        name="Openness.Upper Right",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def upper_right_openness(self):
        if self.eyelid_upper_right:
            return self.eyelid_upper_right.openness

    @upper_right_openness.setter
    def set_upper_right_openness(self, value):
        self.eyelid_upper_right.openness = value

    @upper_right_openness.on_demand
    def on_upper_right_openness_demand(self, value):
        self._last_demand = now()
        self.set_upper_right_openness(value)

    @parameter(
        "float",
        name="Openness.Upper Right Feedback",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def upper_right_openness_feedback(self):
        if self.eyelid_upper_right:
            return self.eyelid_upper_right.feedback

    @upper_right_openness_feedback.setter
    def set_upper_right_openness_feedback(self, value):
        self.eyelid_upper_right.feedback = value

    @parameter(
        "float",
        name="Openness.Upper Left",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def upper_left_openness(self):
        if self.eyelid_upper_left:
            return self.eyelid_upper_left.openness

    @upper_left_openness.setter
    def set_upper_left_openness(self, value):
        self.eyelid_upper_left.openness = value

    @upper_left_openness.on_demand
    def on_upper_left_openness_demand(self, value):
        self._last_demand = now()
        self.set_upper_left_openness(value)

    @parameter(
        "float",
        name="Openness.Upper Left Feedback",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def upper_left_openness_feedback(self):
        if self.eyelid_upper_left:
            return self.eyelid_upper_left.feedback

    @upper_left_openness_feedback.setter
    def set_upper_left_openness_feedback(self, value):
        self.eyelid_upper_left.feedback = value

    @parameter(
        "float",
        name="Openness.Lower Right",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def lower_right_openness(self):
        if self.eyelid_lower_right:
            return self.eyelid_lower_right.openness

    @lower_right_openness.setter
    def set_lower_right_openness(self, value):
        self.eyelid_lower_right.openness = value

    @lower_right_openness.on_demand
    def on_lower_right_openness_demand(self, value):
        self._last_demand = now()
        self.set_lower_right_openness(value)

    @parameter(
        "float",
        name="Openness.Lower Right Feedback",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def lower_right_openness_feedback(self):
        if self.eyelid_lower_right:
            return self.eyelid_lower_right.feedback

    @lower_right_openness_feedback.setter
    def set_lower_right_openness_feedback(self, value):
        self.eyelid_lower_right.feedback = value

    @parameter(
        "float",
        name="Openness.Lower Left",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def lower_left_openness(self):
        if self.eyelid_lower_left:
            return self.eyelid_lower_left.openness

    @lower_left_openness.setter
    def set_lower_left_openness(self, value):
        self.eyelid_lower_left.openness = value

    @lower_left_openness.on_demand
    def on_lower_left_openness_demand(self, value):
        self._last_demand = now()
        self.set_lower_left_openness(value)

    @parameter(
        "float",
        name="Openness.Lower Left Feedback",
        min_value=SQUEEZED_CLOSED,
        max_value=WIDE_OPEN,
    )
    def lower_left_openness_feedback(self):
        if self.eyelid_lower_left:
            return self.eyelid_lower_left.feedback

    @lower_left_openness_feedback.setter
    def set_lower_left_openness_feedback(self, value):
        self.eyelid_lower_left.feedback = value


##############################################################################


class Eyelid:
    def __init__(self, control, bid):
        self._bid = bid
        self._control = control
        self._openness = NORMAL_OPEN
        self._blinking_openness = NORMAL_CLOSED
        self.blinking = False
        self.dirty = False
        self.feedback = None

    @property
    def control_pair(self):
        return (self._control.name, self._control.namespace)

    def blink(self, until, openness):
        was_blinking = self.blinking
        self.blinking = True
        self._blinking_until = until
        self._blinking_openness = openness
        if not was_blinking:
            self.dirty = True

    def maybe_unblink(self, t):
        if self.blinking and self._blinking_until < t:
            self.blinking = False
            self.dirty = True

    @property
    def openness(self):
        return self._openness

    @openness.setter
    def openness(self, value):
        v = clamp(value, SQUEEZED_CLOSED, WIDE_OPEN)
        if self._openness != v:
            self._openness = v
            if not self.blinking:
                self.dirty = True

    @property
    def openness_with_blinking(self):
        if self.blinking:
            return self._blinking_openness
        else:
            return self._openness

    def update_from_clip(self, clip, force):
        if force or self.dirty:
            openness = self.openness_with_blinking

            value = clip.curves[self.control_pair].sample(openness)
            with self._bid.use():
                try:
                    self._control.demand = value
                except Exception as e:
                    print(f"{self.control_pair} error: {e}")
            self.dirty = False