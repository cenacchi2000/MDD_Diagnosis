"""
Add a short description of your script here

See https://tritiumrobot.cloud/docs/ for more information
"""


class Activity:
    def on_start(self):  # self.set_debug_value
        system.messaging.post(
            "play_sequence",
            "Animations.dir/System.dir/Chat Expressions.dir/Chat_G2_Happy_1.project",
        )
