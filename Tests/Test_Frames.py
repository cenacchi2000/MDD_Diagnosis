from tritium.world.geom import Point3


class Activity:
    def on_start(self):
        self.space_magic = system.world.converter(
            system.world.ROBOT_SPACE, "Right Eye Camera"
        )

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=10)
    def on_tick(self):
        try:
            v = Point3([0, 0, 0])
            converted = self.space_magic.convert(v)
            print(converted)
        except TypeError:
            pass
