"""
Loads layered LookAt Config for use by other scripts.

If you can make your robot-specific customizations by editing Config/Robot/LookAt.py that is
much preferable to editing either this file or Config/Default/LookAt.py.

By editing the "Robot" file it's easy to reset/update the default values without removing
these per-robot customizations.
"""

UTILS = system.import_library("./utils.py")

DEFAULT_CONFIG_MODULE = system.import_library("./Default/LookAt.py")
ROBOT_CONFIG_MODULE = system.try_import_library("./Robot/LookAt.py")

CONFIG = UTILS.module_to_dict(DEFAULT_CONFIG_MODULE)

# Layer robot-specific config on top
if ROBOT_CONFIG_MODULE is not None:
    ROBOT_CONFIG = UTILS.module_to_dict(ROBOT_CONFIG_MODULE)
    # Contributors is a dict - we allow the robot overlay to be sparse
    CONFIG["CONTRIBUTORS"].update(ROBOT_CONFIG.pop("CONTRIBUTORS", {}))
    # All other settings are merged as-is
    CONFIG.update(ROBOT_CONFIG)
