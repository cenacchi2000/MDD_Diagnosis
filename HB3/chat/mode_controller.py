from typing import Any, Optional

ENVIRONMENT_KNOWLEDGE = system.import_library("./knowledge/environment_knowledge.py")
Mode = system.import_library("./modes/mode.py").Mode


_singleton = None


class ModeController:
    """Controls the modes on the robot."""

    def __init__(self, modes: dict[str, Mode], start_mode: str):
        self.MODES = modes
        self.mode = None
        self.mode_name = None

        global _singleton
        _singleton = self

        if not self.set_mode(start_mode):
            raise Exception("Unrecognised mode: ", start_mode)

    def set_mode(self, mode_name: str) -> bool:
        if mode_name not in self.MODES:
            return False
        if self.mode_name is not None:
            self.mode.on_mode_exit()
        last_mode_name = self.mode_name
        self.mode_name = mode_name
        self.mode = self.MODES[mode_name]
        self.mode.on_mode_entry(last_mode_name)
        return True

    async def on_message(self, channel: str, message: Any):
        if channel == "mode_change":
            self.set_mode(message)
        elif self.mode:
            # Create the task in a separate coroutine
            await self.mode.on_message(channel, message)

    @staticmethod
    def get_current_mode_name() -> Optional[str]:
        if _singleton is not None:
            return _singleton.mode_name
        return None