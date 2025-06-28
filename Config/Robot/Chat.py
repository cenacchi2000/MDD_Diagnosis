"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""


MODES: list[str] = ["silent", "interaction", "conference", "custom_interaction", "pakdd_aiforum_interaction"]

AVAILABLE_INTERACTION_ACTIONS: list[str] = [
    "turn_volume_up",
    "turn_volume_down",
    "change_head_colour",
    "do_joke",
    "get_robot_serial",
    "reply_with_visual_context",
    "remember_voice_with_name",
    "select_voice",
    "show_facial_expression",
    "get_conversational_topic",
    "search_knowledge_base",
    
    # "recognize_faces",
    # "recognize_action_from_vid", # reply_with_visual_context seems to be better
    # "mimic_emotion",
]
