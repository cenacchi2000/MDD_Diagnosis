CONFIG = system.import_library("../Config/HB3.py").CONFIG
UTILS = system.import_library("./utils.py")


if CONFIG["ROBOT_TYPE"] in [
    CONFIG["ROBOT_TYPES"].AMECA,
    CONFIG["ROBOT_TYPES"].AMECA_DRAWING,
]:
    robot_specific_scripts = [
        "./Look_At/Torso_Look_At.py",
        "./Human_Animation/Add_Body_Breathing.py",
        "./Human_Animation/Add_Body_Neutral.py",
        "./Human_Animation/Anim_Arm_Swing.py",
        "./Human_Animation/Anim_Hands.py",
        "./Human_Animation/Anim_Talking_Arm_Movements.py",
    ]
else:
    robot_specific_scripts = []


SCRIPTS = [
    # Mix Pose MUST be first, in order to be ready to recieve demands
    # from other scripts, especially the neutral pose scripts.
    "./Actuation/Do_Mix_Pose.py",
    "./Human_Animation/Add_Face_Neutral.py",
    "./Look_At/Contributors/Add_Glances.py",
    "./Look_At/Contributors/Add_Idle_Look_Around.py",
    "./Look_At/Contributors/Add_Body_Look_Around.py",
    "./Look_At/Contributors/Add_Sound_Lookaround.py",
    "./Look_At/Contributors/Add_Face_Look_At.py",
    "./Look_At/Contributors/Add_Camera_Look_At.py",
    "./Look_At/Contributors/Add_Telepresence_Look_At.py",
    "./Look_At/Contributors/Add_Gaze_Target_Look_At.py",
    "./Look_At/Base_Decider.py",
    "./Look_At/Eye_Look_At.py",
    "./Look_At/Neck_Look_At.py",
    "./Actuation/Do_Sequence.py",
    "./Actuation/Do_TTS.py",
    "./Actuation/Do_Pose_For_Camera.py",
    "./Perception/Add_Face_Mediapipe.py",
    "./Perception/Process_Faces.py",
    "./Perception/Process_Video.py",
    "./Perception/Do_Speaker_Detection.py",
    "./Human_Animation/Add_Thinking.py",
    "./Human_Animation/Add_Blinking.py",
    "./Human_Animation/Anim_Lipsync.py",
    "./Human_Animation/Add_Proximity_Recoil.py",
    "./Viz/Visualize_Robot_Speech.py",
    "./Shutdown_Button_Monitor.py",
] + robot_specific_scripts

llm_interface = system.import_library("./lib/llm/llm_interface.py")

default_voice_reset_evt = system.event("default_voice_reset")


class Activity:
    async def on_start(self):
        await llm_interface.start()
        for script_path in SCRIPTS:
            UTILS.start_other_script(system, script_path)

    def on_stop(self):
        default_voice_reset_evt.emit(__file__)
        for script_path in reversed(SCRIPTS):
            UTILS.stop_other_script(system, script_path)
        llm_interface.stop()


def _resolve_path(path, my_path):
    if not path.startswith("/"):
        parts = [*my_path.split("/")[:-1]]
        for p in path.split("/"):
            if p == ".":
                continue
            elif p == "..":
                parts.pop()
            else:
                parts.append(p)
        resolved = "/".join(parts)
    else:
        resolved = path[1:]
    return resolved