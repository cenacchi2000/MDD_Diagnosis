"""
Add a short description of your script here

See https://tritiumrobot.cloud/docs/ for more information
"""


class Activity:
    def on_start(self):  # self.set_debug_value
        system.messaging.post(
            "tts_say",
            {
                "message": "Why doge no fluff",
                "language_code": "eng",
                "is_thinking": True,
            },
        )
