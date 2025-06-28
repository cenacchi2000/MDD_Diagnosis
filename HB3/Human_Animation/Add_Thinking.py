"""
Plays a thinking animation while preparing response
"""

import random

STATIC_CONFIG = system.import_library("../../Config/Static.py").BASE_CONTENT_PATH
CONFIG = system.import_library("../../Config/Chat.py").CONFIG
robot_state = system.import_library("../robot_state.py").state


DIR = "Thinking_Anims"
THINKING_ANIMS = [
    "thinking_face_1.project",
    "thinking_face_2.project",
    "thinking_face_3.project",
    "thinking_face_4.project",
]

"""
These determine the thinking characteristics of the robot
"""
PROBABILITY_OF_SOUND = 0.15


class Activity:
    thinking_activity = None

    def on_stop(self):
        self.stop_thinking()

    def on_message(self, channel, message):
        if channel == "is_thinking":
            if message:
                self.start_thinking()
            else:
                self.stop_thinking()

    def stop_thinking(self):
        # thinking sound is interrupted on first LLM response (see HB3/chat/modes/llm_decider_mode.py)
        if self.thinking_activity:
            system.unstable.state_engine.stop_activity(
                cause="stopped within script", activity=self.thinking_activity
            )
            self.thinking_activity = None

    def start_thinking(self):
        self.play_thinking_sound()
        self.play_thinking_animation()

    def play_thinking_animation(self):
        # pick a random project
        path = STATIC_CONFIG + "Animations.dir/System.dir/Chat Thinking.dir/"
        animation_file = random.choice(THINKING_ANIMS)
        self.thinking_activity = system.unstable.state_engine.start_activity(
            cause="started within script",
            activity_class="playing_sequence",
            properties={
                "file_path": f"{path}{animation_file}",
                "precedence": Precedence.HIGH,
            },
            on_stop=self._on_thinking_activity_stopped,
        )

    def _on_thinking_activity_stopped(self, stop_info):
        if stop_info.activity == self.thinking_activity and robot_state.is_thinking:
            self.play_thinking_animation()

    def play_thinking_sound(self):
        if random.uniform(0, 1) > 1 - PROBABILITY_OF_SOUND:
            lang_code = robot_state.last_language_code
            if lang_code not in robot_state.all_languages:
                lang_code = "eng"

            system.messaging.post(
                "tts_say",
                {
                    "message": "",
                    "language_code": lang_code,
                    "is_thinking": "short",
                },
            )