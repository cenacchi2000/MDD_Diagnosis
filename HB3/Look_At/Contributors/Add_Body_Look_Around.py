import random
from time import time_ns as time_unix_ns
from time import monotonic
from itertools import count

from tritium.world import World
from ea.util.random import random_generator
from tritium.world.geom import Point3

contributor = system.import_library("../../lib/contributor.py")

LOOKAT_CONFIG = system.import_library("../../../Config/LookAt.py").CONFIG


DELAY = random_generator(*LOOKAT_CONFIG["BODY_LOOKAROUND_DELAY"])

Y_RANGE = LOOKAT_CONFIG["BODY_LOOKAROUND_Y_RANGE"]
MAX_Y_MOVEMENT = LOOKAT_CONFIG["BODY_LOOKAROUND_MAX_MOVEMENT"]
Z_RANGE = LOOKAT_CONFIG["BODY_LOOKAROUND_Z_RANGE"]
# Robot is about 1.7m tall


class Activity:
    contributor = None
    last_y = 0

    def on_start(self):
        self._count = count()
        self.contributor = contributor.Contributor(
            "look",
            "look_around_body",
            reference_frame=World.ROBOT_SPACE,
        )
        self.contributor.add(self.new_item())
        self.next_item_time = monotonic() + next(DELAY)
        self.last_y = 0

    def new_item(self):
        i = next(self._count)
        return contributor.LookAtItem(
            identifier=f"body_look_around_{i}",
            position=self.new_position(),
            sample_time_ns=time_unix_ns(),
        )

    def new_position(self):
        x = 2
        z = random.uniform(*Z_RANGE)

        y_min = max(Y_RANGE[0], self.last_y - MAX_Y_MOVEMENT)
        y_max = min(Y_RANGE[1], self.last_y + MAX_Y_MOVEMENT)

        y = random.uniform(y_min, y_max)

        probe("xyz", (x, y, z))

        return Point3([x, y, z])

    def on_message(self, t, d):
        if self.contributor:
            self.contributor.on_message(t, d)

    @system.tick(fps=5)
    async def on_tick(self):
        t = monotonic()
        if t > self.next_item_time:
            self.contributor.update([self.new_item()])
            self.next_item_time = t + next(DELAY)