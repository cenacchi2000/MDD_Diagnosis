import re
import json
import asyncio
from abc import abstractmethod
from typing import Any, Optional
from inspect import signature

from openai import APIError, APITimeoutError

llm_model = system.import_library("../../lib/llm/llm_models.py")

CONFIG = system.import_library("../../../Config/Chat.py").CONFIG
INTERACTION_HISTORY = system.import_library("../knowledge/interaction_history.py")

mode = system.import_library("./mode.py")
stream_module = system.import_library("../lib/stream_outputs.py")
robot_state = system.import_library("../../robot_state.py").state
PARENT_ITEM_ID = system.import_library("../actions/action_util.py").PARENT_ITEM_ID


class LLMDeciderMode(mode.Mode):
    """A mode in which we use LLM to decide what to do."""

    ############## Required properties ###################

    @property
    @abstractmethod
    def DECISION_MODEL(self) -> llm_model.LLMModel:
        """LLM model to use"""
        pass

    ############## Provided methods ###################
    def reset(self):
        pass

    async def on_message(self, channel: str, message: Any):
        """Called when a system message is received.

        Args:
            channel (str): the channel the message was sent on
            message (Any): the message content
        """
        if channel == "speech_recognized":
            robot_state.set_thinking(True)
            robot_state.start_response_task(
                self.recursively_call_llm(
                    parent_item_id=message.get("id", None),
                    purpose="process ASR",
                )
            )

    async def try_call_function(
        self,
        function_call: dict[str, str],
        is_tool_call=True,
        call_id: str = "",
        decision_model: llm_model.LLMModel | None = None,
        parent_item_id: Optional[str] = None,
    ) -> bool:
        """Try to call a function.

        Args:
            function_call: a dictionary with keys describing the function call.
              - "name" is the name of the function to be called
              - "arguments" is the set of kwargs to be passed to the function

        Returns:
            true if we should go back to the LLM with the result or there was a simple
            failure and we need to retry for that reason
        """
        PARENT_ITEM_ID.set(parent_item_id)
        decision_model = (
            self.DECISION_MODEL if decision_model is None else decision_model
        )
        # We first validate that the function being called matches openai's own regex.
        # Otherwise we could return it in the history and get a 400 error...
        if not re.fullmatch("[a-zA-Z0-9_-]{1,64}", function_call["name"]):
            log.warning("LLM returned an invalid function name. Retrying.")
            return True  # Try again...

        function_call_parsed = function_call

        function_name = function_call_parsed["name"]
        function_args = function_call_parsed["arguments"]

        # Add the call event to memory
        call_event = (
            INTERACTION_HISTORY.ToolCallEvent(
                call_id=call_id,
                function_name=function_name,
                function_arguments=function_args,
            )
            if is_tool_call
            else INTERACTION_HISTORY.FunctionCallEvent(
                function_name=function_name,
                function_arguments=function_args,
            )
        )

        decision_model.interaction_history.add_to_memory(call_event)

        function_args = (
            function_args
            if isinstance(function_args, dict)
            else json.loads(function_args)
        )

        log.info(f"Action call: {function_name}({function_args})")

        should_call_again = False
        if function_name in decision_model.full_map:
            function_info = decision_model.full_map[function_name]
            should_call_again = function_info["requires_subsequent_function_calls"]

            # Check the function call is valid
            function = function_info["function"]
            function_signature = signature(function)
            if any(
                [k not in function_signature.parameters for k in function_args.keys()]
            ) or any(
                [
                    k not in function_args
                    for k, v in function_signature.parameters.items()
                    if v.default is v.empty
                ]
            ):
                log.warning("INVALID ARGUMENTS for function call! Ignoring...")
                result = {
                    "status": "call failed",
                    "error": "INVALID ARGUMENTS for function call! Ignoring...",
                }

            try:
                result = await function(**function_args)
                if isinstance(result, tuple):
                    call_finished, call_result = result
                else:
                    call_finished = True
                    call_result = result

                if call_finished:
                    result = {"status": "call returned successfully"}
                    if call_result:
                        result["result"] = call_result
                else:
                    result = {
                        "status": "in progress",
                        "update": call_result,
                    }

            except asyncio.CancelledError as e:
                # CancelledError inherits from BaseException, not Exception, so the except below wouldn't catch it
                log.warning(f"Function {function_name} was cancelled: {e}")
                result = {"status": "call cancelled", "error": str(e)}
            except Exception as e:
                log.exception(str(e), warning=True)
                result = {"status": "call failed", "error": str(e)}
            finally:
                call_event.add_response(
                    json.dumps(result), decision_model.interaction_history
                )
        else:
            log.warning(
                "LLM returned unrecognized function: {function_name}, Ignoring..."
            )

            call_event.add_response(
                json.dumps(
                    {
                        "status": "call failed",
                        "error": f"LLM returned unrecognized function: {function_name}, Ignoring...",
                    }
                ),
                decision_model.interaction_history,
            )

            should_call_again = True
        return should_call_again

    async def recursively_call_llm(
        self,
        decision_model: llm_model.LLMModel | None = None,
        output_stream: stream_module.StreamOutput = stream_module.streamToTTS,
        specified_message_prompt: tuple[str, str] | None = None,
        max_recursion: int = 5,
        parent_item_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ):
        decision_model = (
            self.DECISION_MODEL if decision_model is None else decision_model
        )
        last_parent_item_id = parent_item_id

        async def call_llm():
            nonlocal last_parent_item_id
            messages = (
                await decision_model.get_message_prompt()
                if specified_message_prompt is None
                else await decision_model.get_specified_message_prompt(
                    *specified_message_prompt
                )
            )

            if CONFIG["LLM_LOGGING"]:
                log_lines = (
                    ["[LLM Call] - Messages:"]
                    + [str(message) for message in messages]
                    + ["", "[LLM Call] - Functions:"]
                )
                if decision_model.full_map:
                    log_lines.append(f"{list(decision_model.full_map.keys())}")
                else:
                    log_lines.append("None")

                log.info("\n".join(log_lines))

            # Wait for the decision model to run
            response_stream = await decision_model(
                messages,
                parent_item_id=last_parent_item_id,
                purpose=purpose,
            )
            if response_stream is None:
                return False
            should_call_again = False
            first_res: bool = True
            active_index: int = 0
            try:
                async for response in response_stream:

                    if CONFIG["LLM_LOGGING"]:
                        log.info(f"[LLM Response] - {response}")

                    # backwards compatible flattening, direct OpenAI LLM interface do not support `choice`
                    if "choice" in response:
                        response.update(response["choice"]["delta"])
                        response["index"] = response["choice"]["index"]
                        if first_res:
                            # add reply validation here
                            active_index = response["choice"]["index"]
                            first_res = False

                    last_parent_item_id = response.get("item_id", None)

                    if ("index" not in response) or (response["index"] == active_index):
                        if tool_calls := response.get("tool_calls", False):
                            for call in tool_calls:
                                if call["type"] == "function":
                                    should_call_again = (
                                        await self.try_call_function(
                                            call["function"],
                                            is_tool_call=True,
                                            call_id=call.get("id", ""),
                                            decision_model=decision_model,
                                            parent_item_id=last_parent_item_id,
                                        )
                                        or should_call_again
                                    )
                                else:
                                    log.warning(
                                        f"Unexpected `type` in `tool_calls`: {tool_calls}"
                                    )
                        else:
                            lang_code = response.get("language", None)
                            await output_stream(
                                response["content"],
                                {
                                    "lang_code": lang_code,
                                    "parent_item_id": last_parent_item_id,
                                },
                            )
                system.messaging.post("llm_finished", "LLM Finished")
            except (APITimeoutError, APIError) as e:
                log.warning(f"OpenAI Error: {e}")
            robot_state.set_thinking(False)
            return should_call_again

        # call_llm returns True if you need to call it again
        try:
            n_recursion: int = 0
            while await call_llm():
                n_recursion += 1
                if n_recursion >= max_recursion:
                    log.warning(
                        f"LLMDeciderMode.recursively_call_llm() with {decision_model}, reach the maximum recursion count of {max_recursion}"
                    )
                    break
                purpose = f"recursive call {n_recursion}"
        except asyncio.CancelledError:
            robot_state.set_thinking(False)
            log.info("Recursive LLM Call cancelled early")
        except Exception:
            robot_state.set_thinking(False)
            log.exception("LLM Error:")