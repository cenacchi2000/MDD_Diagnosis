import random

from tritium.world.geom import Point3


class Activity:
    def on_start(self):
        self._t = 0
        self._dt = 0.01

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=10)
    def on_tick(self):
        if random.random() < 0.9:
            return
        x = random.uniform(0, 0.5)
        y = random.uniform(-0.3, 0.3)
        z = random.uniform(1.8, 1.6)

        # x = 1
        # y = 0 + self._t
        # z = 1.8
        # self._t += self._dt
        # if self._t < -0.5 or self._t > 0.5:
        #    self._dt = -self._dt
        probe("t", self._t)
        probe("target", (x, y, z))
        system.messaging.post("eye_look_at", Point3([x, y, z]))