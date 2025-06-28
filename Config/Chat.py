"""
Loads layered Chat Config for use by other scripts.

If you can make your robot-specific customizations by editing Config/Robot/Chat.py that is
much preferable to editing either this file or Config/Default/Chat.py.

By editing the "Robot" file it's easy to reset/update the default values without removing
these per-robot customizations.
"""

UTILS = system.import_library("./utils.py")
get_layered_config = UTILS.get_layered_config
clean_phrase = UTILS.clean_phrase


CONFIG_MODULE = system.import_library("./Default/Chat.py")
ROBOT_CONFIG_MODULE = system.try_import_library("./Robot/Chat.py")

CONFIG = get_layered_config(CONFIG_MODULE, ROBOT_CONFIG_MODULE)

HB3_CONFIG = system.import_library("./HB3.py").CONFIG

CONFIG["AVAILABLE_INTERACTION_ACTIONS"] = CONFIG["AVAILABLE_INTERACTION_ACTIONS"]

if HB3_CONFIG["ROBOT_TYPE"] == HB3_CONFIG["ROBOT_TYPES"].AMECA_DRAWING:
    CONFIG["AVAILABLE_INTERACTION_ACTIONS"] += [
        "draw",
        "stop_drawing",
        "recognise_users_drawing_game",
        "recognise_drawing",
        "show_gesture_drawing_robot",
    ]
else:
    # we have a special show gesture builder for drawing robot that prevents gestures when robot is drawing,
    # and a special set of gestures meant just for the drawing robot that does not hit the board
    CONFIG["AVAILABLE_INTERACTION_ACTIONS"].append("show_gesture")

CONFIG["IGNORE_PHRASES"] = [clean_phrase(p) for p in CONFIG["IGNORE_PHRASES"]]

CONFIG["INTERACTION_HIDDEN_SYS_MSG"] = CONFIG["INTERACTION_HIDDEN_SYS_MSG"]
