from abc import ABCMeta
from typing import Any, Optional


class Mode(metaclass=ABCMeta):
    """This is the base class for a mode.

    Modes must inherit from this class to be compatible with the function decider.

    BoiMode(Mode):
        def on_mode_exit(self):
            do_pog()
    """

    ############## Methods ###################

    def on_mode_exit(self):
        """Runs when you exit the mode."""
        pass

    def on_mode_entry(self, from_mode_name: Optional[str]):
        """Runs when you enter the mode.

        Args:
            from_mode_name (Optional[str]): the mode you have come from
        """
        pass

    async def on_message(self, channel: str, message: Any):
        """Called when a system message is recieved.

        Args:
            channel (str): the channel the message was sent on
            message (Any): the message content
        """
        pass