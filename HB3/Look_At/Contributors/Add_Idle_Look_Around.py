import random
from time import time_ns as time_unix_ns
from time import monotonic
from itertools import count

from ea.util.random import random_generator
from tritium.world.geom import Point3

contributor = system.import_library("../../lib/contributor.py")

LOOKAT_CONFIG = system.import_library("../../../Config/LookAt.py").CONFIG


DELAY = random_generator(*LOOKAT_CONFIG["LOOKAROUND_DELAY"])

Y_RANGE = LOOKAT_CONFIG["LOOKAROUND_Y_RANGE"]
# Robot is about 1.7m tall
Z_RANGE = LOOKAT_CONFIG["LOOKAROUND_Z_RANGE"]


def get_zones(range_: tuple[float, float], n_zones: int) -> set[tuple[float, float]]:
    zone_size = (range_[1] - range_[0]) / n_zones
    return zone_size, [range_[0] + i * zone_size for i in range(n_zones)]


Y_ZONE_SIZE, Y_ZONES = get_zones(Y_RANGE, LOOKAT_CONFIG["LOOKAROUND_N_Y_ZONES"])
Z_ZONE_SIZE, Z_ZONES = get_zones(Z_RANGE, LOOKAT_CONFIG["LOOKAROUND_N_Z_ZONES"])

ZONE_COOLDOWN_TIME = LOOKAT_CONFIG["LOOKAROUND_ZONE_COOLDOWN_TIME"]


class Activity:
    contributor = None
    available_lookat_zones = []
    cooldown_lookat_zones = []

    def on_start(self):
        self._count = count()
        self.contributor = contributor.Contributor(
            "look",
            "look_around",
            reference_frame=system.world.ROBOT_SPACE,
        )
        self.contributor.add(self.new_item())
        self.available_lookat_zones = [(y, z) for y in Y_ZONES for z in Z_ZONES]
        self.cooldown_lookat_zones = []
        self.next_item_time = monotonic() + next(DELAY)

    def new_item(self):
        i = next(self._count)
        return contributor.LookAtItem(
            identifier=f"look_around_{i}",
            position=self.new_position(),
            sample_time_ns=time_unix_ns(),
        )

    def new_position(self):
        x = 2
        probe("Available Zones", self.available_lookat_zones)
        probe("TimedOut Zones", self.cooldown_lookat_zones)
        if len(self.available_lookat_zones) > 0:
            # Pick a zone at random
            zone_index = random.randint(0, len(self.available_lookat_zones) - 1)
            zone = self.available_lookat_zones.pop(zone_index)
            # Make the robot ignore that zone for a cooldown period
            self.cooldown_lookat_zones.append((zone, monotonic() + ZONE_COOLDOWN_TIME))
            y = zone[0] + random.uniform(0, Y_ZONE_SIZE)
            z = zone[1] + random.uniform(0, Z_ZONE_SIZE)
        else:
            # There are no zones left - just pick in the full range
            y = random.uniform(*Y_RANGE)
            z = random.uniform(*Z_RANGE)

        probe("xyz", (x, y, z))

        return Point3([x, y, z])

    def on_message(self, t, d):
        if self.contributor:
            self.contributor.on_message(t, d)

    @system.tick(fps=5)
    async def on_tick(self):
        t = monotonic()
        if t > self.next_item_time:
            # Add zones which have had the cooldown period back in
            while (
                len(self.cooldown_lookat_zones) > 0
                and self.cooldown_lookat_zones[0][1] < t
            ):
                zone, _ = self.cooldown_lookat_zones.pop(0)
                self.available_lookat_zones.append(zone)

            # We need a new item really...
            self.contributor.update([self.new_item()])
            self.next_item_time = t + next(DELAY)