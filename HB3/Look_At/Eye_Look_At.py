from time import monotonic
from random import choice

from ea.math3d import Vector3 as V3
from ea.math3d import to_spherical_position
from ea.util.number import clamp, step_towards
from ea.util.random import random_generator

contributor = system.import_library("../lib/contributor.py")

eye_yaw_left = system.control("Eye Yaw Left", "Mesmer Eyes 1", acquire=["min", "max"])
eye_yaw_right = system.control("Eye Yaw Right", "Mesmer Eyes 1", acquire=["min", "max"])

eye_pitch_left = system.control(
    "Eye Pitch Left", "Mesmer Eyes 1", acquire=["min", "max"]
)
eye_pitch_right = system.control(
    "Eye Pitch Right", "Mesmer Eyes 1", acquire=["min", "max"]
)

SLEW_RATE = 90000000  # TODO: Make this framerate independent
SACCADE_INTERVAL = random_generator(1, 3)


class Activity:
    glances = None
    looks = None
    _last_aid = None

    def on_start(self):
        self.looks = contributor.Consumer("look")

        self.yaw_r = 0
        self.pitch_r = 0
        self.yaw_l = 0
        self.pitch_l = 0

        self.last_changed_saccade = monotonic()
        self.next_saccade_interval = next(SACCADE_INTERVAL)
        self.saccade_index = 0

        self.bid = system.arbitration.make_bid(
            specifiers=["Control/Mesmer Eyes 1"],
            precedence=Precedence.VERY_HIGH,
            bid_type=BidType.ON_DEMAND,
        )
        # Needs to be higher than sequences. Almost all control will go through this.

        self.send()

    def maybe_change_saccade(self):
        def get_new_saccade_index(active):
            if active.saccades:
                if len(active.saccades) > 1:
                    return choice(
                        [
                            s
                            for s in range(len(active.saccades))
                            if not s == self.saccade_index
                        ]
                    )
                else:
                    return 0
            return None

        active = self.looks.active
        if not active:
            return
        aid = (active.config.identifier, active.identifier)
        t = monotonic()
        if aid != self._last_aid:
            self._last_aid = aid
            # Reset saccade counter
            self.last_changed_saccade = t

            self.saccade_index = get_new_saccade_index(active)
        elif t > self.last_changed_saccade + self.next_saccade_interval:
            self.saccade_index = get_new_saccade_index(active)
            probe("saccade_index", self.saccade_index)
            self.last_changed_saccade = t
            self.next_saccade_interval = next(SACCADE_INTERVAL)

    def on_message(self, t, d):
        if self.looks:
            self.looks.on_message(t, d)

    def send(self):
        with self.bid.use():
            eye_pitch_left.demand = self.pitch_l
            probe("pitch_l", self.pitch_l)
            eye_pitch_right.demand = self.pitch_l
            probe("pitch_r", self.pitch_r)
            eye_yaw_left.demand = self.yaw_l
            probe("yaw_l", self.yaw_l)
            eye_yaw_right.demand = self.yaw_r
            probe("yaw_r", self.yaw_r)

    _num = 0

    @system.tick(fps=40)
    def on_tick(self):
        # Run updates at a lower rate but in sync with look-at tick
        # We slew the positions and perform the geometry at the higher rate
        # But choose what to look at a little slower as an optimisation
        if self._num % 2 == 0:
            self.looks.update_choices(probe_fn=probe)
            self.maybe_change_saccade()
        self._num += 1

        right = self.looks.get_current_position("Right Eye Neutral", self.saccade_index)
        left = self.looks.get_current_position("Left Eye Neutral", self.saccade_index)
        probe("l", left)
        probe("r", right)
        if not left or not right:
            return

        sph_l = to_spherical_position(V3(*left.elements))
        sph_r = to_spherical_position(V3(*right.elements))
        probe("sph_l", sph_l)
        probe("sph_r", sph_r)

        d_yaw_l = sph_l.phi_degrees - self.yaw_l
        d_yaw_r = sph_r.phi_degrees - self.yaw_r

        self.yaw_l = step_towards(self.yaw_l, sph_l.phi_degrees, SLEW_RATE)
        self.yaw_r = step_towards(self.yaw_r, sph_r.phi_degrees, SLEW_RATE)

        probe("d_yaw_l", d_yaw_l)
        probe("d_yaw_r", d_yaw_r)

        self.pitch_l = step_towards(self.pitch_l, sph_l.theta_degrees, SLEW_RATE)
        self.pitch_r = step_towards(self.pitch_r, sph_r.theta_degrees, SLEW_RATE)
        min_yaw = min(eye_yaw_left.min or 0, eye_yaw_right.min or 0)
        max_yaw = max(eye_yaw_left.max or 0, eye_yaw_right.max or 0)
        probe("min_yaw", min_yaw)
        probe("max_yaw", max_yaw)
        self.yaw_l = clamp(self.yaw_l, min_yaw, max_yaw)
        self.yaw_r = clamp(self.yaw_r, min_yaw, max_yaw)

        min_pit = min(eye_pitch_left.min or 0, eye_pitch_right.min or 0)
        max_pit = max(eye_pitch_left.max or 0, eye_pitch_right.max or 0)
        probe("min_pit", min_pit)
        probe("max_pit", max_pit)
        self.pitch_l = clamp(self.pitch_l, min_pit, max_pit)
        self.pitch_r = clamp(self.pitch_r, min_pit, max_pit)

        self.send()