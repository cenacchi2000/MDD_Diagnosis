"""
https://tritiumrobot.cloud/docs/

Add a short description of your script here
"""


class Activity:
    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    def on_message(self, channel, message):
        probe(channel, message)

    @system.tick(fps=10)
    def on_tick(self):
        pass
