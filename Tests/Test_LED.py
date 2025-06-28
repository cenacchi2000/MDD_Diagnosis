"""
Add a short description of your script here

See https://tritiumrobot.cloud/docs/ for more information
"""


class Activity:
    def on_start(self):  # self.set_debug_value
        system.messaging.post("set_led", (1, 1, 0))
