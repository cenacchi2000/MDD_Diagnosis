from time import monotonic


class Activity:
    ok = False

    @system.tick(fps=10)
    def on_tick(self):
        self.ok = not self.ok
        if self.ok:
            probe("joe", monotonic())
            probe("yeah", monotonic())
