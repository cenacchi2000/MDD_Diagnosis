"""
Disable certain human-like behaviour provided by the system for research experiments.

See https://docs.engineeredarts.co.uk/ for more information
"""
import os
CONFIG = system.import_library("../../../Config/HB3.py").CONFIG
UTILS = system.import_library("../../../HB3/utils.py")

EXPRESSION_DECIDER = system.import_library(
    "../../../HB3/chat/lib/determine_tts_face_expression.py"
)

SEQUENCE_PATH = "Animations.dir/System.dir/Chat Expressions.dir"

IGNORE = []

SCRIPTS = [
    "../../../HB3/Human_Animation/Add_Blinking.py",   
]


class Activity:

    def on_start(self):
        self.exp_decider = EXPRESSION_DECIDER.TTSFaceExpression.from_animation_dir(SEQUENCE_PATH)
        self.start_other_scripts()
        # self.play_sequence("Demo_Exp_Angry_1")
    

    def on_stop(self):
        # self.play_sequence("Demo_Exp_Angry_1")
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    def start_other_scripts(self):
        for script_path in SCRIPTS:
            UTILS.start_other_script(system, script_path)
        pass
    
    def get_sequence_path_from_name(self, sequence_name):
        return os.path.join(SEQUENCE_PATH, f"{sequence_name}.project")


    def stop_all_talking_anims(self):
        to_stop = []
        for anim in self.exp_decider.expressions:
            to_stop.append(self.get_sequence_path_from_name(anim))
        system.messaging.post("stop_sequence", to_stop)

    def play_sequence(self, sequence_name):
        path = self.get_sequence_path_from_name(sequence_name)
        self.stop_all_talking_anims()
        system.messaging.post("play_sequence", path)


    @system.tick(fps=10)
    def on_tick(self):
        pass

        

