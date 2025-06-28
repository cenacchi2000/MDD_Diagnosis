"""
This script simulates speech recognition. Depending on the message content
you trigger LLM function call (for example, by asking for a joke), trigger
interruption by starting this script while robot is talking and so on.

See https://tritiumrobot.cloud/docs/ for more information
"""

from uuid import uuid4


class Activity:
    def on_start(self):
        msg = "Tell me a joke"
        # msg = "Tell me a story about three squirrels in the woods eating peanuts"
        # msg = "I'm bored - please stop!"
        system.messaging.post(
            "speech_recognized",
            {
                "text": msg,
                "id": str(uuid4()),
            },
        )
        self.stop()
