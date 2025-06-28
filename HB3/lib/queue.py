import math
from time import monotonic as now

from ea.animation import INTERP_BEZIER, INTERP_COSINE
from ea.animation.structural import Clip


def clip_last_nodes(clip):
    for ctrl, curve in clip.curves.items():
        if curve.nodes:
            yield ctrl, curve, curve.nodes[-1]


def is_silence(viseme_name):
    return viseme_name in ("", "sil")


class Queue:
    start_time = None
    _finished = False
    _last_viseme = None

    MAX_INTERP_TIME = 0.08

    def __init__(self):
        self.clip = Clip({}, [])

    def started(self, offset=0):
        self.start_time = now() + offset

    def finished(self):
        self._finished = True

    def is_finished(self):
        return self._finished

    def control_names(self):
        return self.clip.curves.keys()

    def time_till_finish(self):
        return self.clip.duration() - (now() - self.start_time)

    def is_ready(self):
        if self.start_time is None:
            return False
        if self.clip.duration() <= 0:
            return False
        if now() - self.start_time > self.clip.duration():
            self.finished()
            return False
        return True

    # Could be useful for combinatorial poses or different interp rates between pose
    # types. Not implemented properly yet.
    # def _last_was_silence():
    #     return is_silence(self._last_viseme)
    def get_blended_pose(self, pose, t):
        # Scale the pose from neutral based on the configured gain.
        blended_pose = {}
        for ctrl, v in pose.items():
            blended_pose[ctrl] = v * t
        return blended_pose

    def to_neutral(self, pose_name, time, delay=0):
        self.clip.add_pose(self.get_blended_pose(pose_name, 1), time, INTERP_COSINE)

    def add_pose_plateau_curve(
        self, pose, time, delay=0, a=-6.4, b=-1.1, DROPOFF_TIME=0.2, gain=1
    ):
        # Make a plateau shape and then quickly drop off afterwards
        # https://www.desmos.com/calculator/zt7wmrkcyp
        sample_amount = 100
        for x in range(0, sample_amount):
            t = 1 - math.exp(a * (x / sample_amount))
            last_time = time * (x / sample_amount) + delay
            self.clip.add_pose(
                self.get_blended_pose(pose, t * gain), last_time, INTERP_COSINE
            )
        for x in range(0, sample_amount):
            t = 1 - math.exp(a * (x / sample_amount)) * b - 1
            last_time = time + DROPOFF_TIME * (x / sample_amount) + delay
            self.clip.add_pose(
                self.get_blended_pose(pose, t * gain), last_time, INTERP_COSINE
            )

    def add_pose(self, pose, weight, time, viseme_name):
        # People rarely move their mouth slowly whilst talking (except for expression)
        # Sometimes TTS will leave a big gap between sentances - we want to detect these
        # gaps and not have a slow interpolation during the gap - instead we hang at the
        # previous keyframe. To further this, for silence keyframes we don't interpolate
        # out at-all, we use step interpolation - so mouth opens sudenly
        d = self.clip.duration()
        if (time - d) > self.MAX_INTERP_TIME:
            previous_pose = self.clip.sample_curves(d)
            self.clip.add_pose(
                previous_pose, time - self.MAX_INTERP_TIME, INTERP_COSINE
            )

        # If the weight is truthy - take a look at the previous keyframes and adjust the
        # interpolation to give this keyframe more "weight".
        # TODO: weight should be 0-1
        if weight:
            for ctrl, curve, node in clip_last_nodes(self.clip):
                curve.add(
                    node.t,
                    node.v,
                    INTERP_BEZIER,
                    ((node.t, pose[ctrl]), (node.t, pose[ctrl])),
                )

        self.clip.add_pose(pose, time, INTERP_COSINE)
        self._last_viseme = viseme_name

    def sample(self):
        return self.clip.sample_curves(now() - self.start_time)

    def __repr__(self):
        # Clip.__repr__ not deployed yet
        cr = f"Clip({dict(self.clip.curves.items())!r}, {self.clip.events!r})"
        return f"Queue<{cr}>"