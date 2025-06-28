"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""
SEQUENCE_PATH = "Animations.dir/System.dir/Chat Expressions.dir"
UTILS = system.import_library("../../../HB3/utils.py")

SCRIPTS = [
    "../../../HB3/Look_At/Contributors/Add_Glances.py",
    "../../../HB3/Look_At/Contributors/Add_Idle_Look_Around.py",
    "../../../HB3/Look_At/Contributors/Add_Body_Look_Around.py",
    "../../../HB3/Look_At/Contributors/Add_Sound_Lookaround.py",
    "../../../HB3/Look_At/Contributors/Add_Face_Look_At.py",
    "../../../HB3/Look_At/Contributors/Add_Camera_Look_At.py",
    "../../../HB3/Look_At/Contributors/Add_Telepresence_Look_At.py",
    "../../../HB3/Look_At/Contributors/Add_Gaze_Target_Look_At.py",

    "../../../HB3/Human_Animation/Add_Blinking.py",
    "../../../HB3/Human_Animation/Add_Face_Neutral.py",
    "../../../HB3/Human_Animation/Add_Proximity_Recoil.py",
    "../../../HB3/Human_Animation/Add_Lipsync.py",
    "../../../HB3/Human_Animation/Add_Talking_Sequence.py",
    
]


def stop_other_scripts():
    for script_path in SCRIPTS:
        UTILS.stop_other_script(system, script_path)
    pass

    
def start_other_scripts():
    for script_path in SCRIPTS:
        not UTILS.is_other_script_running(system, script_path) and UTILS.start_other_script(system, script_path)


# class Activity:

#     def on_start(self):
#         start_other_scripts()

#     def on_stop(self):
#         stop_other_scripts()