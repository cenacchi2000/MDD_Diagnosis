from typing import Any, Optional

CONFIG = system.import_library("../../../Config/Chat.py").CONFIG
HB3_CONFIG = system.import_library("../../../Config/HB3.py").CONFIG
MODE_MODEL = "gpt-4o-mini"
ROBOT_STATE = system.import_library("../../robot_state.py")
llm_decider_mode = system.import_library("./llm_decider_mode.py")
gpt_model = system.import_library("../../lib/llm/llm_models.py")
system_actions = system.import_library("../actions/system_actions.py")

ACTION_UTIL = system.import_library("../actions/action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry

CHAT_MODES = CONFIG["MODES"]
DEFAULT_MODE = "interaction"
# DEFAULT_MODE = system.import_library("../../modes_config.py").STARTING_MODE

PERSONA_UTIL = system.import_library("../../lib/persona_util.py")

MODE_NAME = "silent"


class SilentMode(llm_decider_mode.LLMDeciderMode):
    """Robot does not interact, but waits to be told to interact again."""

    DECISION_MODEL = None
    BACKEND_PARAMS = {"max_tokens": 40, "tool_choice": "required"}

    def get_system_message(self):
        """Get the system message with current robot name."""
        robot_name = PERSONA_UTIL.get_robot_name()
        return f"""You are a robot called `{robot_name}` in a noisy environment.
Determine if the user wants to change the `mode of operation` or if the message should be ignored because it is irrelevant noise.
When asked to enter a particular mode of operation, enter the specified mode.
When asked to "Start listening", "Leave silent mode", "Start talking again", "Wake up" and so on change the `mode of operation` to `{DEFAULT_MODE}`.
"""

    def get_action_registry(self) -> None:
        async def ignore_noise():
            """Call this when you determine that the message is just noise and should be ignored"""
            pass

        # specify mode transition
        other_modes = [
            mode for mode in CHAT_MODES if mode != MODE_NAME
        ]  # cant change to the current mode
        additional_builders: list[ACTION_UTIL.ActionBuilder] = (
            [system_actions.ChangeModeOfOperation(other_modes)]
            if HB3_CONFIG["ROBOT_TYPE"] != HB3_CONFIG["ROBOT_TYPES"].AMECA_DRAWING
            else [system_actions.ChangeModeOfOperation(["drawing"])]
        )
        return ActionRegistry(actions=[ignore_noise], builders=additional_builders)

    def on_mode_entry(self, from_mode_name: Optional[str]):
        """Called when you enter silent mode.

        Args:
            from_mode_name (Optional[str]): the mode you have come from
        """

        self.DECISION_MODEL = gpt_model.LLMModel(
            model=MODE_MODEL,
            system_message=self.get_system_message(),
            action_registry=self.get_action_registry(),
            history_limit=4,
            history=ROBOT_STATE.interaction_history,
            backend_params=self.BACKEND_PARAMS,
        )

        if from_mode_name is not None:
            system.messaging.post("tts_say", ["Entering silent mode", "eng"])

    async def on_message(self, channel: str, message: Any):
        """Called when a system message is received.

        Overwrite the default behaviour so that we don't have the thinking face

        Args:
            channel (str): the channel the message was sent on
            message (Any): the message content
        """

        # Do not allow the recursive LLM calls to actually do any TTS in this mode
        if channel == "speech_recognized":
            await self.recursively_call_llm(
                output_stream=llm_decider_mode.stream_module.dummyStream,
                parent_item_id=message.get("id", None),
                purpose="silent mode",
            )


MODE = SilentMode