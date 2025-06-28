import os

CONFIG = system.import_library("../../Config/HB3.py").CONFIG

EXPRESSION_DECIDER = system.import_library(
    "../chat/lib/determine_tts_face_expression.py"
)

SEQUENCE_PATH = "Animations.dir/System.dir/Chat Expressions.dir"

IGNORE = []


class Activity:
    playing_sequence = None

    def on_start(self):
        self.exp_decider = EXPRESSION_DECIDER.TTSFaceExpression.from_animation_dir(
            SEQUENCE_PATH
        )

    def get_sequence_path_from_name(self, sequence_name):
        return os.path.join(SEQUENCE_PATH, f"{sequence_name}.project")

    async def on_message(self, channel, message):
        if channel == "tts_saying":
            # NOTE: Different to tts_say
            selected_exp = await self.exp_decider.determine_tts_face_expression(
                message.speech,
                parent_item_id=message.item_id,
            )
            if selected_exp and selected_exp not in IGNORE:
                self.play_sequence(selected_exp)
            else:
                log.warning(f"Invalid expression `{selected_exp}` ignored")

        elif channel == "tts_idle":
            self.stop_all_talking_anims()

    def stop_all_talking_anims(self):
        to_stop = []
        for anim in self.exp_decider.expressions:
            to_stop.append(self.get_sequence_path_from_name(anim))
        system.messaging.post("stop_sequence", to_stop)

    def play_sequence(self, sequence_name):
        path = self.get_sequence_path_from_name(sequence_name)
        self.stop_all_talking_anims()
        system.messaging.post("play_sequence", path)