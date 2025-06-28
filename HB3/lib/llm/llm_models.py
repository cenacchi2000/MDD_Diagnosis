from typing import Callable, Optional, AsyncGenerator

FUNCTION_PARSER = system.import_library("./function_parser.py")
INTERACTION_HISTORY = system.import_library(
    "../../chat/knowledge/interaction_history.py"
)
# ENVIRONMENT_KNOWLEDGE = system.import_library(
#     "../../chat/knowledge/environment_knowledge.py"
# )

ACTION_UTIL = system.import_library("../../chat/actions/action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry

llm_interface = system.import_library("./llm_interface.py")
gpt_utils = system.import_library("./openai/utils.py")
get_image_b64 = system.import_library(
    "../../Perception/lib/get_image.py"
).get_good_frame


class LLMModel:
    def __init__(
        self,
        model: str,
        system_message: str,
        history: INTERACTION_HISTORY.InteractionHistory | None,
        action_registry: ActionRegistry = ActionRegistry(),
        history_limit: int = 10,
        backend_params: Optional[dict[str, any]] = None,
    ):
        """Initialise a LLMModel class.

        Args:
            model: LLM model to use
            system_message: The system message for prompting the LLM
            history: The interaction history
            functions: The functions the model is allowed to call
            history_limit: The number of interactions to include in the prompt
            backend_params: to be passed to the backend
        """
        self.model = model
        self.set_system_message(system_message)
        self.history_limit = history_limit

        self.action_registry = action_registry
        action, self.action_builders = self.action_registry.get()
        self.set_actions(action)
        if backend_params:
            self.backend = backend_params
        else:
            self.backend = {}
        self.interaction_history = (
            history if history is not None else INTERACTION_HISTORY.InteractionHistory()
        )

    def set_system_message(self, system_message) -> None:
        """
        Set system message which is used for prompting the LLM.

        Args:
            system_message: message to set.
        """
        self.system_messages = [
            {"role": "system", "content": [{"type": "text", "text": system_message}]}
        ]

    def set_actions(self, functions: Optional[list[Callable]]):
        """Set the Action.

        Args:
            functions: the functions to set
        """
        if functions:
            self.functions_map = FUNCTION_PARSER.get_functions_prompt_map(functions)
        else:
            self.functions_map = None

    def set_model(self, model: str) -> None:
        """
        Set the model to be used by the LLM.

        Args:
            model: The name or identifier of the model to set.
        """
        self.model = model

    def set_backend_params(self, backend_params: dict[str, any]) -> None:
        """
        Set the backend parameters for the LLM.

        Args:
            backend_params: A dictionary containing backend parameters to update.

        """
        self.backend.update(backend_params)

    @property
    def full_map(self):
        # This assumes none of the functions have the same name (should be a safe assumption)
        factory_funcs = []
        for builder in self.action_builders:
            factory_funcs.extend(builder.factory())
        factory_function_map = FUNCTION_PARSER.get_functions_prompt_map(factory_funcs)
        # merge the dicts
        if self.functions_map is not None:
            return factory_function_map | self.functions_map
        else:
            return factory_function_map

    @property
    def functions_prompt(self):
        ret = []
        ret.extend(fun["prompt"] for fun in self.full_map.values())
        if ret:
            return ret

    async def get_message_prompt(self) -> list[dict]:
        """Get the prompt from the interaction history, profiles etc.

        Returns:
            a list of messages to be passed to the LLM
        """
        conversation = self.interaction_history.to_message_list(self.history_limit)

        # Disable profiles until identity is stable
        # profiles = ENVIRONMENT_KNOWLEDGE.get_profiles()
        messages = self.system_messages + conversation

        return messages

    async def get_specified_message_prompt(
        self, system_msg: str, msg: str
    ) -> list[dict]:
        """Get the prompt from the message

        Returns:
            a list of messages to be passed to the LLM
        """
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_msg}]}
        ] + INTERACTION_HISTORY.SpeechRecognisedEvent(msg).to_messages()
        return messages

    async def __call__(
        self,
        messages: list[dict],
        parent_item_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """Call the model on a set of messages.

        Args:
            messages: run the model on the set of messages

        Yields:
            the responses from LLM
        """
        return await llm_interface.run_chat_streamed(
            model=self.model,
            messages=messages,
            functions=self.functions_prompt,
            parent_item_id=parent_item_id,
            purpose=purpose,
            **self.backend,
        )


class LLMVisionModel(LLMModel):
    SUPPORTED_MODELS = {"gpt-4-vision-preview", "gpt-4-turbo", "gpt-4o"}

    def __init__(
        self,
        model: str,
        system_message: str,
        image_prompt: str,
        history: INTERACTION_HISTORY.InteractionHistory | None,
        action_registry: ActionRegistry = ActionRegistry(),
        history_limit: int = 10,
        backend_params: Optional[dict[str, any]] = None,
    ):
        """Initialise a LLMModel class.

        Args:
            model: OpenAI model to use
            system_message: The system message for prompting the LLM
            functions: The functions the model is allowed to call
            history: The interaction history
            history_limit: The number of interactions to include in the prompt
            backend_params: to be passed to the backend
        """
        if model not in LLMVisionModel.SUPPORTED_MODELS:
            raise Exception(f"Unsupported vision model: {model}")
        super().__init__(
            model=model,
            system_message=system_message,
            history=history,
            action_registry=action_registry,
            history_limit=history_limit,
            backend_params=backend_params,
        )
        self.image_prompt = image_prompt

    async def get_message_prompt(self) -> list[dict]:
        """Get the prompt from the interaction history, profiles etc.

        Returns:
            a list of messages to be passed to the openai api
        """
        image_b64 = await get_image_b64()

        # Vision models do not support function calling!
        messages = [
            m
            for m in (await super().get_message_prompt())
            if ("function_call" not in m)
            and ("tool_calls" not in m)
            and (m["role"] != "function")
            and (m["role"] != "tool")
        ]
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.image_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_b64},
                    },
                ],
            }
        )

        return messages