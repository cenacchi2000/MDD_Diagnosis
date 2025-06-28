ROBOT_STATE = system.import_library("../robot_state.py")
robot_state = ROBOT_STATE.state


class Activity:
    @system.on_event("default_voice_reset")
    def on_chat_stop(self, msg):
        robot_state.reset_to_default_voice()
        log.info(
            f"{msg}: Resetting to the Default Voice due to default_voice_reset event"
        )
