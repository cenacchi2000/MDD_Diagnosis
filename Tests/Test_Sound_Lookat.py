"""
Add a short description of your script here

See https://tritiumrobot.cloud/docs/ for more information
"""

from time import time_ns as time_unix_ns

from tritium.world.geom import Point3

microphone = system.control(
    "Microphone Array", None, acquire=["direction", "voice_activity"]
)

contributor = system.import_library("../HB3/lib/contributor.py")


class Activity:
    DIRECTIONS = [Point3([0.8, 0.4, 1.8]), Point3([0.4, -0.5, 1.8])]
    COUNT = 0
    INDEX = 0

    def on_start(self):
        self.lookat_contributor = contributor.Contributor(
            "look",
            "sound",
            reference_frame=system.world.ROBOT_SPACE,
        )
        self.last_direction = None
        self.cooldown = None

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=1 / 2)
    def on_tick(self):
        self.COUNT += 1
        self.COUNT %= len(self.DIRECTIONS)
        print(self.DIRECTIONS[self.COUNT])
        self.lookat_contributor.add(
            contributor.LookAtItem(
                identifier=f"sound_glance_{self.INDEX}",
                position=self.DIRECTIONS[self.COUNT],
                sample_time_ns=time_unix_ns(),
            )
        )
        self.INDEX += 1