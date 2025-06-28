CHAT_CONFIG = system.import_library("../../../Config/Chat.py").CONFIG
INTERACTION_HIDDEN_SYS_MSG = CHAT_CONFIG["INTERACTION_HIDDEN_SYS_MSG"]

llm_model = system.import_library("../../lib/llm/llm_models.py")
llm_decider_mode = system.import_library("../modes/llm_decider_mode.py")

ROBOT_STATE = system.import_library("../../robot_state.py")
robot_state = ROBOT_STATE.state

PERSONA_UTIL = system.import_library("../../lib/persona_util.py")


system_message_template_idle = """{PERSONALITY}
- Through your eyes you can recognise and see what's infront of you, such as humans and their clothing, drawings or objects.
{INTERACTION_HIDDEN_SYS_MSG}
"""

ACTION_UTIL = system.import_library("./action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry
ActionBuilder = ACTION_UTIL.ActionBuilder
Action = ACTION_UTIL.Action

PARENT_ITEM_ID = ACTION_UTIL.PARENT_ITEM_ID


@ActionRegistry.register_builder
class ReplyWithVisualContext(ActionBuilder):

    def factory(self) -> list[Action]:

        image_prompt = """
        This what the robot can currently see using it's eyes, it is not an image. You are able to describe everything about it.
        """
        system_message, llm_model_name, image_backend_params, _, _ = (
            PERSONA_UTIL.get_llm_persona_info("vision")
        )

        # Inject image hidden prompt
        system_message = system_message_template_idle.format(
            PERSONALITY=system_message,
            INTERACTION_HIDDEN_SYS_MSG=INTERACTION_HIDDEN_SYS_MSG,
        )

        decision_model_image = llm_model.LLMVisionModel(
            model=llm_model_name,
            system_message=system_message,
            image_prompt=image_prompt,
            backend_params=image_backend_params,
            history=ROBOT_STATE.interaction_history,
        )

        async def reply_with_visual_context():
            """Reply to the user's question by analyzing what your eye cameras can see.
            Call this function when the user's question requires visual context to be answered, or do this whenever you wish, especially if it would suprise people.
            Use it to answer the user's query, you must add as much detail as you can.
            For example if the user asks 'what color is my shirt', 'how many fingers am I holding up', or 'what you can see' this function must be called.
            """
            parent_item_id = PARENT_ITEM_ID.get()
            # play long thinking sound
            system.messaging.post(
                "tts_say",
                {
                    "message": "",
                    "language_code": robot_state.last_language_code,
                    "is_thinking": "long",
                    "parent_item_id": parent_item_id,
                },
            )

            messages = await decision_model_image.get_message_prompt()
            action_return_str: str = "Successfully called visual model"
            response = await decision_model_image(
                messages,
                parent_item_id=parent_item_id,
                purpose="vision",
            )
            if response:
                async for chunk in response:
                    msg: str = (
                        chunk["content"]
                        if "content" in chunk
                        else chunk["choice"]["delta"]["content"]
                    )

                    tts_kwargs: dict = {
                        "parent_item_id": chunk.get("item_id", None),
                    }
                    try:
                        tts_kwargs["lang_code"] = chunk["choice"]["delta"]["language"]
                    except KeyError:
                        pass  # No language returned

                    await llm_decider_mode.stream_module.streamToTTS(
                        msg, kwargs=tts_kwargs
                    )
            else:
                action_return_str = "Vision model call failed..."
                log.error(action_return_str)

            return action_return_str

        return [reply_with_visual_context]