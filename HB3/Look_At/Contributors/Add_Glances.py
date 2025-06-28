from time import time_ns as time_unix_ns
from time import monotonic as time_monotonic
from random import random
from itertools import count

from ea.util.random import random_generator
from tritium.world.geom import Point3

stash = system.unstable.stash

contributor = system.import_library("../../lib/contributor.py")
LOOKAT_CONFIG = system.import_library("../../../Config/LookAt.py").CONFIG

ActiveSensor = system.import_library("../../robot_state/ActiveSensor.py").ActiveSensor

DELAY = random_generator(*LOOKAT_CONFIG["GLANCES_PERIOD_RANGE"])
X_DIST = LOOKAT_CONFIG["GLANCES_X_DIST"]
Y_RANGE = random_generator(*LOOKAT_CONFIG["GLANCES_Y_RANGE"])
Z_RANGE = random_generator(*LOOKAT_CONFIG["GLANCES_Z_RANGE"])


class Activity:
    contributor = None
    consumer = None

    def on_start(self):
        self._count = count()
        self.consumer = contributor.ConsumerRef("look")
        self.contributor = contributor.Contributor(
            "look",
            "glance",
            reference_frame=ActiveSensor.get().neutral,
        )
        self._last_glanced_at_time = time_monotonic()
        self.delay = next(DELAY)

    @ActiveSensor.subscribe()
    def on_sensor_update(self, sensor) -> None:
        # Update the reference frame with the new sensor when a change is found
        self.contributor.update_config(reference_frame=sensor.neutral)

    def new_item(self, consumer):
        # TODO: Inspect the look consumer to try and glance at real objects/people
        i = next(self._count)
        return contributor.LookAtItem(
            identifier=f"glance_{i}",
            position=self.new_position(consumer),
            sample_time_ns=time_unix_ns(),
        )

    def new_position(self, consumer):
        x = X_DIST
        y = next(Y_RANGE)
        if random() > 0.5:
            y = -y
        # y = 5
        z = next(Z_RANGE)
        return Point3([x, y, z])

    def on_message(self, t, d):
        if self.consumer:
            self.consumer.on_message(t, d)
        if self.contributor:
            self.contributor.on_message(t, d)

    @system.tick(fps=6)
    async def on_tick(self):
        c = self.consumer.object()
        if c is None:
            return

        time_elapsed = (
            time_monotonic() - c.active_changed_at
            if c.active_changed_at > self._last_glanced_at_time
            else time_monotonic() - self._last_glanced_at_time
        )
        if time_elapsed < self.delay:
            return
        item = self.new_item(c)
        if item:
            self.contributor.update([item])
        self._last_glanced_at_time = time_monotonic()
        self.delay = next(DELAY)