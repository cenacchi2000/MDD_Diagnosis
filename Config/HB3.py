"""
Loads layered HB3 Config for use by other scripts.

If you can make your robot-specific customizations by editing Config/Robot/HB3.py that is
much preferable to editing either this file or Config/Default/HB3.py.

By editing the "Robot" file it's easy to reset/update the default values without removing
these per-robot customizations.
"""

get_layered_config = system.import_library("./utils.py").get_layered_config

CONFIG_MODULE = system.import_library("./Default/HB3.py")
ROBOT_CONFIG_MODULE = system.try_import_library("./Robot/HB3.py")

CONFIG = get_layered_config(CONFIG_MODULE, ROBOT_CONFIG_MODULE)
