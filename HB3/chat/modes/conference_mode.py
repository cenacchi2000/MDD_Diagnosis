from typing import Any, Literal, Optional

PERSONA_MANAGER = system.persona_manager

CHAT_CONFIG = system.import_library("../../../Config/Chat.py").CONFIG
HB3_CONFIG = system.import_library("../../../Config/HB3.py").CONFIG
HISTORY_LIMIT = CHAT_CONFIG["INTERACTION_MODE_HISTORY_LIMIT"]
INTERACTION_HIDDEN_SYS_MSG = CHAT_CONFIG["INTERACTION_HIDDEN_SYS_MSG"]
AVAILABLE_ACTIONS = CHAT_CONFIG["AVAILABLE_INTERACTION_ACTIONS"]
DISABLE_ASR_WHILE_SPEAKING = CHAT_CONFIG["DISABLE_ASR_WHILE_SPEAKING"]
CHAT_MODES = CHAT_CONFIG["MODES"]

#### IMPORTS ####

llm_decider_mode = system.import_library("./llm_decider_mode.py")
mode = system.import_library("./mode.py")
llm_model = system.import_library("../../lib/llm/llm_models.py")

ACTION_UTIL = system.import_library("../actions/action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry

system_actions = system.import_library("../actions/system_actions.py")
interaction_actions = system.import_library("../actions/interaction_actions.py")
vision_actions = system.import_library("../actions/vision_actions.py")

INTERACTION_HISTORY = system.import_library("../knowledge/interaction_history.py")
ROBOT_STATE = system.import_library("../../robot_state.py")
robot_state = ROBOT_STATE.state

PERSONA_UTIL = system.import_library("../../lib/persona_util.py")
INTERACTION_ACTIONS = system.import_library("../actions/interaction_actions.py")

MODE_NAME = "conference"

system_message_template_idle = """{PERSONALITY}
You will also be provided with the conversation up until now.
{INTERACTION_HIDDEN_SYS_MSG}
"""


class ConferenceMode(llm_decider_mode.LLMDeciderMode):
    """The conference mode."""

    DECISION_MODEL = None

    def on_mode_entry(self, from_mode_name: Optional[str]):
        """Called when you enter conference mode.
        Args:
            from_mode_name (Optional[str]): the mode you have come from
        """
        self.reset()

        if from_mode_name is not None:
            system.messaging.post("tts_say", ["Entering conference mode", "eng"])

    def reset(self):
        self.llm_backend_params: dict = {}
        self.talking = False
        self.decision_model_chat = self.create_decision_model_reply()
        self.DECISION_MODEL = self.decision_model_chat
        self.decision_mode_talking = self.create_decision_mode_talking()
        self.decision_model_turn_to_speak = self.create_decision_mode_turn_to_speak()

    def create_decision_model_reply(self):
        available_actions: list[str] = AVAILABLE_ACTIONS

        # specify mode transition
        other_modes = [
            mode for mode in CHAT_MODES if mode != MODE_NAME
        ]  # cant change to the current mode
        additional_builders: list[ACTION_UTIL.ActionBuilder] = [
            system_actions.ChangeModeOfOperation(other_modes)
        ]
        self.action_registry = ActionRegistry(
            available_actions, builders=additional_builders
        )

        (
            system_message,
            llm_model_name,
            self.llm_backend_params,
            _,
            language_voice_map,
        ) = PERSONA_UTIL.get_llm_persona_info("chat")

        robot_state.set_default_language_voice_map(language_voice_map)
        # Inject hidden prompt
        system_message = system_message_template_idle.format(
            PERSONALITY=system_message,
            INTERACTION_HIDDEN_SYS_MSG=(
                INTERACTION_HIDDEN_SYS_MSG
                + f'\nYou can only respond in the following languages: {[l for l in language_voice_map]} (these are ISO 639-3 language codes), when asked to respond with a language not listed say something along the lines of "I don\'t speak that language" with a language listed above.'
                + f"\nYour current `mode of operation` is: `{MODE_NAME}`"
            ),
        )

        # Available models include:
        # gpt-4o, gpt-4
        decision_model_chat = llm_model.LLMModel(
            model=llm_model_name,
            system_message=system_message,
            action_registry=self.action_registry,
            backend_params=self.llm_backend_params,
            history_limit=HISTORY_LIMIT,
            history=ROBOT_STATE.interaction_history,
        )

        decision_model_chat.base_system_prompt = system_message
        return decision_model_chat

    def create_decision_mode_talking(self):

        base_system_prompt = """Your job is to analyse the conversation and decide what to do with the current user input by calling one of the functions."""
        talking_history_limit = 6

        async def ignore_message() -> str:
            """Ignores the user message, you must only use this function if the message is a verbal backchanneling phrase.
            Examples of this include, but are not limited to: 'interesting', 'cool', 'yes'.
            """
            try:
                # find and remove last `SpeechRecognisedEvent` from history
                found: Optional[tuple[int, INTERACTION_HISTORY.SpeechRecognisedEvent]]
                if found := ROBOT_STATE.interaction_history.find(
                    INTERACTION_HISTORY.SpeechRecognisedEvent
                ):
                    ROBOT_STATE.interaction_history.pop(found[0])
                    return "Message ignored"
            except RuntimeError:
                log.exception(
                    "Failed to find, and remove last `SpeechRecognisedEvent` from history"
                )
            return "Failed to ignore message"

        async def process_relevant_message() -> str:
            """Process the message to add to the output.
            Note that by processing the message the current output will be overriden.
            """
            system.messaging.post("tts_stop", True)
            process_relevant_message_prompt = " (Acknowledge and feel free to continue with what you were talking about if relevant to the conversation and you are not asked to change the subject.)"

            try:
                # find and modify last `SpeechRecognisedEvent` from history
                found: Optional[tuple[int, INTERACTION_HISTORY.SpeechRecognisedEvent]]
                if found := ROBOT_STATE.interaction_history.find(
                    INTERACTION_HISTORY.SpeechRecognisedEvent
                ):
                    ROBOT_STATE.interaction_history[
                        found[0]
                    ].event.speech += process_relevant_message_prompt
            except RuntimeError:
                log.exception(
                    "Failed to find, and modify last `SpeechRecognisedEvent` from history"
                )

            system.messaging.post("tts_continue", None)
            robot_state.start_response_task(
                self.recursively_call_llm(
                    decision_model=self.decision_model_chat,
                    purpose="keep talking",
                )
            )
            return "Processing message"

        backend_config = self.llm_backend_params.copy()
        backend_config.update(
            {"tool_choice": "required"}
        )  # Model can only use tool calls
        self.talking_action_registry: ActionRegistry = ActionRegistry(
            action_ids=["stop_talking"],
            actions=[ignore_message, process_relevant_message],
        )

        decision_mode_talking = llm_model.LLMModel(
            model="gpt-4o-mini",
            system_message=base_system_prompt,
            history=None,
            action_registry=self.talking_action_registry,
            history_limit=talking_history_limit,
            backend_params=backend_config,
        )
        decision_mode_talking.base_system_prompt = base_system_prompt
        return decision_mode_talking

    def create_decision_mode_turn_to_speak(self):

        base_system_prompt = """Your job is to determine if it is your turn to speak. Always respond if you are directly addressed. Commands to change the `mode of operation` always requires a response and should never be ignored. Information about you, and the conversation so far is provided below."""
        turn_to_speak_history_limit = HISTORY_LIMIT

        # async def ignore_message() -> str:
        #     """Ignores the user message, use this function if the message does not require a response because it is not adressed to you."""
        #     return "Message ignored"

        # TODO: This is a temporary solution to allow the ignore_message function to be used with a gesture
        # TODO: In the future, we should expand the ActionBuilder constructor to allow for a customisable action, eg action descriptions, and REQUIRES_SUBSEQUENT_FUNCTION_CALLS
        class IgnoreMessageWithGesture(ACTION_UTIL.ActionBuilder):

            animation_search_path: str = (
                "Animations.dir/System.dir/Conference Gestures.dir"
            )

            def factory(self) -> list[ACTION_UTIL.Action]:
                """A factory to generate the show_facial_expression function."""
                gesture_sequences = INTERACTION_ACTIONS._search_animations(
                    self.animation_search_path
                )

                # Add "None" to the list of gestures as a default
                gesture_sequences = (
                    tuple() if gesture_sequences is None else gesture_sequences
                )
                gesture_sequences = tuple(["None"]) + gesture_sequences

                async def ignore_message_with_gesture(
                    gesture: Literal[gesture_sequences] = "None",
                ) -> Optional[str]:
                    """Ignores the user message, and optionally show a gesture.
                    Use this function if the message does not require a response because it is not adressed to you and does not request to change the `mode of operation`.
                    The name of the gestures end with a number denoting the intensity of the gesture, the higher the number the more intense the gesture.
                    Args:
                        gesture (str): Name of the gesture to show. Defaults to `None`.
                    """

                    if not gesture or gesture == "None":
                        return
                    return INTERACTION_ACTIONS._play_animation(
                        self.animation_search_path, gesture
                    )

                return [ignore_message_with_gesture]

        async def respond_to_message() -> str:
            """Process the message and respond"""
            robot_state.set_thinking(True)
            robot_state.start_response_task(
                self.recursively_call_llm(
                    decision_model=self.decision_model_chat,
                    purpose="keep talking",
                )
            )
            return "Processing message"

        backend_config = self.llm_backend_params.copy()
        # Model can only use tool calls
        backend_config.update({"tool_choice": "required"})
        self.turn_to_speak_action_registry: ActionRegistry = ActionRegistry(
            actions=[respond_to_message],
            builders=[IgnoreMessageWithGesture()],
        )

        decision_mode_turn_to_speak = llm_model.LLMModel(
            model="gpt-4o",
            system_message=base_system_prompt,
            history=None,
            action_registry=self.turn_to_speak_action_registry,
            history_limit=turn_to_speak_history_limit,
            backend_params=backend_config,
        )
        decision_mode_turn_to_speak.base_system_prompt = base_system_prompt
        return decision_mode_turn_to_speak

    async def on_message(self, channel: str, message: Any):
        """Called when a system message is received.

        Args:
            channel (str): the channel the message was sent on
            message (Any): the message content
        """
        if channel == "speech_recognized":
            if not robot_state.speaking:
                turn_to_speak_prompt: str = (
                    f"{self.decision_model_turn_to_speak.base_system_prompt}\n\n```\n{self.decision_model_chat.base_system_prompt}```\n\nContext:\n```\n{ROBOT_STATE.interaction_history.to_text(self.decision_model_turn_to_speak.history_limit)}\n```"
                )
                robot_state.start_response_task(
                    self.recursively_call_llm(
                        decision_model=self.decision_model_turn_to_speak,
                        output_stream=llm_decider_mode.stream_module.dummyStream,
                        specified_message_prompt=(
                            turn_to_speak_prompt,
                            message.get("text"),
                        ),
                        parent_item_id=message.get("id", None),
                        purpose="determine turn to speak",
                    )
                )
            elif not DISABLE_ASR_WHILE_SPEAKING:
                robot_state.start_process_task(
                    self.recursively_call_llm(
                        decision_model=self.decision_mode_talking,
                        output_stream=llm_decider_mode.stream_module.dummyStream,
                        specified_message_prompt=(
                            self.decision_mode_talking.base_system_prompt
                            + f"Context:\n{ROBOT_STATE.interaction_history.to_text(self.decision_mode_talking.history_limit)}",
                            (
                                ROBOT_STATE.interaction_history.last_recognized_speech_event().to_text()
                                if ROBOT_STATE.interaction_history.last_recognized_speech_event()
                                else message.get("text")
                            ),
                        ),
                        parent_item_id=message.get("id", None),
                        purpose="handle interruption",
                    )
                )
        elif channel == "non_verbal_interaction_trigger":
            if not robot_state.speaking:
                robot_state.start_response_task(
                    self.recursively_call_llm(
                        decision_model=self.decision_model_chat,
                        purpose="non-verbal interaction",
                    )
                )


MODE = ConferenceMode