"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""
# import importlib
# INTERACTION_MODE_MODULE = system.import_library("./chat/modes/interaction_mode.py")
# SLEEP_MODE_MODULE = system.import_library("./chat/modes/silent_mode.py")
# CONFERENCE_MODE_MODULE = system.import_library("./chat/modes/conference_mode.py")

# MODE_MODULES = [
#     INTERACTION_MODE_MODULE,
#     SLEEP_MODE_MODULE,
#     CONFERENCE_MODE_MODULE,
# ]
CHAT_CONF = system.import_library("../../../Config/Chat.py").CONFIG

MODE_CONF = system.import_library("../../../HB3/modes_config.py")
CUSTOM_INTERACTION_MODULE = system.import_library("../Chat/Modes/custom_interaction_mode.py")
PAKDD_INTERACTION_MODULE = system.import_library("../Chat/Modes/Oneshot_Modes/pakdd_ai_forum.py")

class Activity:
    def on_start(self):
        # starting_mode = 'custom_interaction'
        MODE_CONF.STARTING_MODE = 'pakdd_aiforum_interaction'  # custom_interaction
        configured_modules = MODE_CONF.MODE_MODULES
        if len(configured_modules) >= len(CHAT_CONF["MODES"]):
            print(f'already configured!!!')
            self.stop()
            # MODE_CONF.MODE_MODULES[-1] = CUSTOM_INTERACTION_MODULE  # TODO repalce the last one
            return
        MODE_CONF.MODE_MODULES.append(CUSTOM_INTERACTION_MODULE)
        MODE_CONF.MODE_MODULES.append(PAKDD_INTERACTION_MODULE)
        print(f'len mode modules: {len(MODE_CONF.MODE_MODULES)}')
        self.stop()

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=10)
    def on_tick(self):
        pass
