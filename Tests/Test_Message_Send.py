"""
https://tritiumrobot.cloud/docs/

Add a short description of your script here
"""


class Activity:
    def on_start(self):
        self._t = 0

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=10)
    def on_tick(self):
        self._t += 1
        system.messaging.post("Test", self._t)
