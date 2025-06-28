"""This describes the modes which are available.

This file should be overwritten when new modes are added.
"""

INTERACTION_MODE_MODULE = system.import_library("./chat/modes/interaction_mode.py")
SLEEP_MODE_MODULE = system.import_library("./chat/modes/silent_mode.py")
CONFERENCE_MODE_MODULE = system.import_library("./chat/modes/conference_mode.py")

MODE_MODULES = [
    INTERACTION_MODE_MODULE,
    SLEEP_MODE_MODULE,
    CONFERENCE_MODE_MODULE,
]

STARTING_MODE = "interaction"
