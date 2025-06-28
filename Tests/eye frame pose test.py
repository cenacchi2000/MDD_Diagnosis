from tritium.world.geom import Point3


class Activity:
    def on_start(self):
        self.right_eye_convert = system.world.converter(
            system.world.ROBOT_SPACE, "Left Eye Neutral"
        )
        self.left_eye_convert = system.world.converter(
            system.world.ROBOT_SPACE, "Left Eye Neutral"
        )

    @system.tick(fps=10)
    def on_tick(self):
        target = Point3([0.5, 0, 1.71])
        try:
            target_l = self.left_eye_convert.convert(Point3(target))
            target_r = self.right_eye_convert.convert(Point3(target))
        except AttributeError:
            pass
        else:
            probe("target", target)
            probe("target_l", target_l)
            probe("target_r", target_r)
