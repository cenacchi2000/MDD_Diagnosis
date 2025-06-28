import math
from time import time_ns as time_unix_ns
from time import monotonic
from itertools import count

from tritium.world.geom import Point3

LOOKAT_CONFIG = system.import_library("../../../Config/LookAt.py").CONFIG

VAD = system.import_library("../../Perception/VAD_subscription.py").VAD

microphone = system.control("Microphone Array", None, acquire=["direction"])

contributor = system.import_library("../../lib/contributor.py")

perception_state = system.import_library(
    "../../Perception/perception_state.py"
).perception_state


class Activity:
    contributor = None

    def on_start(self):
        # Subscribe to the VAD
        VAD.executed_functions.handle(self.check_VAD_change)
        self.vad = False
        self.contributor = contributor.Contributor(
            "look",
            "sound",
            reference_frame=system.world.ROBOT_SPACE,
        )
        self.contributor.clear()
        self._count = count()
        self.sound_history = []

    def check_VAD_change(self, data: dict):
        # If theres been a change in VAD
        if self.vad is not None:
            if data["detected"] and not self.vad:
                self.look_at()
        self.vad = data["detected"]

    def on_message(self, t, d):
        if self.contributor:
            self.contributor.on_message(t, d)

    def look_at(self):
        if microphone.direction is not None:
            doa = 90 - microphone.direction
            if any(
                [
                    abs(doa - item[1]) < LOOKAT_CONFIG["SOUND_DIFF_THRESHOLD"]
                    for item in self.sound_history
                ]
            ):
                return
            self.sound_history.append((monotonic(), doa))
            x, y = math.cos(math.radians(doa)), math.sin(math.radians(doa))
            probe("doa", doa)

            item_position = Point3([x, y, perception_state.average_face_height])
            probe("Item position", item_position)

            self.contributor.update(
                [
                    contributor.LookAtItem(
                        identifier=f"sound_look_{next(self._count)}",
                        position=item_position,
                        sample_time_ns=time_unix_ns(),
                    )
                ]
            )

    @system.tick(fps=1)
    def on_tick(self):
        probe("sound_history", self.sound_history)

        time_monotonic = monotonic()
        # Expire old sounds
        self.sound_history = [
            item
            for item in self.sound_history
            if time_monotonic - item[0] < LOOKAT_CONFIG["SOUND_COOLDOWN_TIME"]
        ]