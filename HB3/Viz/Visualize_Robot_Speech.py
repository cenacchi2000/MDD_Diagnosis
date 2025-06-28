from time import time as time_unix

from tritium.world.geom import Point3

TYPES = system.import_library("../lib/types.py")
speech_publisher = system.world.publish(
    "ameca_speech",
    TYPES.SpeechBubble,
    display={
        "bubble": "speak",
        "remove": {"animation": "fade", "duration": 5000, "floatDistance": 1},
    },
)
TextToSpeechNodeClient = system.import_library(
    "../Actuation/lib/tts_client.py"
).TextToSpeechNodeClient


ROBOT_HEAD_POSITION = Point3([0, 0, 1.85])

CLEARING_ITEM = TYPES.SpeechBubble(None, ROBOT_HEAD_POSITION, -1)


class Activity:
    last_tts_item_id = None

    def on_message(self, channel, message):
        if channel == "tts_item_finished":
            said, id_ = message
            speech_publisher.write(TYPES.SpeechBubble(said, ROBOT_HEAD_POSITION, id_))

    @system.tick(fps=10)
    def on_tick(self):
        time = time_unix()
        if ret := TextToSpeechNodeClient.get_current_sentence(time):
            said, item_id = ret
            if item_id is not None:
                speech_publisher.write(
                    TYPES.SpeechBubble(said, ROBOT_HEAD_POSITION, item_id)
                )
        else:
            speech_publisher.write(CLEARING_ITEM)