"""
Log all the events which occurs in the short term.
"""

import json
import uuid
import weakref
from abc import abstractmethod
from time import time as time_unix
from typing import Literal, ClassVar, Optional
from dataclasses import asdict, dataclass

PERSONA_UTIL = system.import_library("../../lib/persona_util.py")
TYPES = system.import_library("../../lib/types.py")


DEFAULT_LOG_COLOR = "white"


@dataclass
class TTSEventData:
    description: str
    log_color: str

    voice_info: TYPES.TTSVoiceInfo
    speech_item: TYPES.SpeechItem

    interaction_type: ClassVar[str] = "tts"


@dataclass
class InteractionEventData:
    interaction_type: str
    description: str
    log_color: str


class InteractionEvent:
    interaction_type: ClassVar[str]
    openai_role: ClassVar[Optional[str]] = None
    log_color: ClassVar[str] = DEFAULT_LOG_COLOR

    @abstractmethod
    def to_text(self) -> Optional[str]:
        """Return the event as a string to be printed into the interaction history.

        Returns:
            A description of the event.
        """
        pass

    def to_ui_text(self) -> Optional[str]:
        """Return the event as a string to be displayed in Viz UI.

        Returns:
            A description of the event.
        """
        return self.to_text()

    def to_messages(self) -> Optional[list[dict]]:
        """Return the event as a message to be printed into the interaction history.

        Returns:
            A description of the event.
        """
        text_content = self.to_text()
        if self.openai_role and text_content is not None:
            return [
                {
                    "role": self.openai_role,
                    "content": [{"type": "text", "text": text_content}],
                }
            ]
        return None

    def try_conflate(self, next_event) -> Optional["InteractionEvent"]:
        return None

    def to_event_data(self):
        return InteractionEventData(
            self.interaction_type,
            self.to_ui_text(),
            self.log_color,
        )


@dataclass(slots=True)
class FunctionCallResponseEvent(InteractionEvent):
    interaction_type: ClassVar[str] = "function_response"
    event_emitter = system.world.declare_event(
        event_name="function_response", data_type=InteractionEventData
    )

    function_name: str
    function_response: str
    conflatable: bool = False

    openai_role: ClassVar[Optional[str]] = "function"
    log_color: ClassVar[str] = "silver"

    def to_text(self) -> Optional[str]:
        return f'Function Call Response:"{self.function_response}"'

    def to_messages(self) -> Optional[list[dict]]:
        return [
            {
                "role": self.openai_role,
                "name": self.function_name,
                "content": [{"type": "text", "text": self.function_response}],
            }
        ]

    def try_conflate(self, next_event) -> Optional[InteractionEvent]:
        if not isinstance(next_event, FunctionCallResponseEvent):
            return None

        if self.function_name != next_event.function_name:
            return None

        if not self.conflatable or not next_event.conflatable:
            return None

        return next_event


@dataclass(slots=True)
class FunctionCallEvent(InteractionEvent):
    event_emitter = system.world.declare_event(
        event_name="function_call", data_type=InteractionEventData
    )

    interaction_type = "function_call"
    function_name: str
    function_arguments: str

    openai_role: ClassVar[Optional[str]] = "assistant"
    log_color: ClassVar[str] = "silver"

    def add_response(
        self, response_message: str, interaction_history: Optional["InteractionHistory"]
    ):
        assert (
            interaction_history is not None
        ), "Attempt to add response for function call with no interaction history"
        interaction_history.add_to_memory(
            FunctionCallResponseEvent(self.function_name, response_message, False)
        )

    def to_messages(self) -> Optional[list[dict]]:
        # Reformat the output. OpenAI will throw a wobbly if "tool_calls" is in there
        return [
            {
                "role": self.openai_role,
                "content": None,
                "function_call": {
                    "name": self.function_name,
                    "arguments": self.function_arguments,
                },
            }
        ]


@dataclass(slots=True)
class ToolCallResponseEvent(InteractionEvent):
    event_emitter = system.world.declare_event(
        event_name="function_tool_response", data_type=InteractionEventData
    )

    interaction_type = "function_tool_response"
    function_name: str
    function_response: str
    call_id: str = ""

    openai_role: ClassVar[Optional[str]] = "tool"
    log_color: ClassVar[str] = "gray"

    def to_text(self) -> Optional[str]:
        return f'Tool Call Response: "{self.function_response}"'

    def to_messages(self) -> Optional[list[dict]]:
        return [
            {
                "role": self.openai_role,
                "tool_call_id": self.call_id,
                "name": self.function_name,
                "content": [{"type": "text", "text": self.function_response}],
            }
        ]


@dataclass(slots=True)
class ToolCallEvent(InteractionEvent):
    event_emitter = system.world.declare_event(
        event_name="tool_call", data_type=InteractionEventData
    )
    interaction_type = "tool_call"

    function_name: str
    function_arguments: str
    call_id: str = ""

    _responses: list[ToolCallResponseEvent] = None

    openai_role: ClassVar[Optional[str]] = "assistant"
    log_color: ClassVar[str] = "gray"

    def to_text(self) -> str | None:
        if self._responses:
            res_text: list[str] = [r.to_text() for r in self._responses if r.to_text()]
            return "\n".join(res_text)
        return

    def to_ui_text(self) -> str | None:
        """
        We give to_text to the LLM sometimes and if we include the function name and arguments,
        it can get confused and think it can call it again. So we have to have separate text
        for the UI.
        """
        return f'"{self.function_name}", with arguments: "{self.function_arguments}"'

    def add_response(
        self, response_message: str, _: Optional["InteractionHistory"] = None
    ):
        evt = ToolCallResponseEvent(self.function_name, response_message, self.call_id)
        if self._responses is not None:
            self._responses.append(evt)
        else:
            self._responses = [evt]
        evt.event_emitter.emit(evt.to_event_data())

    def to_messages(self) -> Optional[list[dict]]:
        own_message = [
            {
                "role": self.openai_role,
                "content": None,
                "tool_calls": [
                    {
                        "type": "function",
                        "id": self.call_id,
                        "function": {
                            "name": self.function_name,
                            "arguments": self.function_arguments,
                        },
                    }
                ],
            }
        ]

        # If no response has come through yet, just send a response message explaining this.
        # This is for compatibility with what openai expects
        last_response = (
            self._responses[-1]
            if self._responses
            else ToolCallResponseEvent(
                self.function_name,
                function_response=json.dumps(
                    {
                        "status": "In Progress",
                        "update": "Function called, but has not returned yet.",
                    }
                ),
                call_id=self.call_id,
            )
        )

        return last_response.to_messages() + own_message


@dataclass(slots=True)
class TTSEvent(InteractionEvent):
    interaction_type: ClassVar[str] = "tts"
    event_emitter = system.world.declare_event(event_name="tts", data_type=TTSEventData)

    finished_event_emitter = system.world.declare_event(
        event_name="tts_finished",
        data_type=InteractionEventData,
    )

    voice_info: TYPES.TTSVoiceInfo
    speech_item: TYPES.SpeechItem
    synch_words: Optional[list[(int, str)]] = None
    _finished: bool = False

    openai_role: ClassVar[Optional[str]] = "assistant"
    log_color: ClassVar[str] = "gray"
    finished_log_color: ClassVar[str] = "aqua"

    def get_said_at_time(self, time) -> str | None:
        if self._finished:
            return self.speech_item.speech
        elif self.synch_words is not None:
            said = None
            for said_time, subsaid in self.synch_words:
                if time < said_time:
                    break
                else:
                    said = subsaid + "..."
            else:
                said = self.speech_item.speech
        else:
            return self.speech_item.speech
        return said

    def stop(self, time):
        if not self._finished:
            self.speech_item.speech = self.get_said_at_time(time)
            self._finished = True

            # Send an event indicating what was actually said
            self.finished_event_emitter.emit(
                InteractionEventData(
                    "tts_finished",
                    (
                        self.speech_item.speech
                        if self.speech_item.speech is not None
                        else "..."
                    ),
                    self.finished_log_color,
                )
            )

    def to_text(self) -> Optional[list[dict]]:
        said = self.get_said_at_time(time_unix())
        if said is None:
            return None
        return (
            f'{PERSONA_UTIL.get_robot_name()} said: "{said}"'
            if self._finished
            else f'{PERSONA_UTIL.get_robot_name()} saying: "{said}"'
        )

    def to_messages(self) -> Optional[list[dict]]:
        """Return the event as a message to be printed into the interaction history.

        Returns:
            A description of the event.
        """
        if self.speech_item.is_thinking:
            return None
        said = self.get_said_at_time(time_unix())
        if said is None:
            return None

        return [
            {
                "role": self.openai_role,
                "content": [{"type": "text", "text": said}],
            }
        ]

    def try_conflate(self, next_event) -> Optional["TTSEvent"]:
        if not isinstance(next_event, TTSEvent):
            return None

        if self.voice_info != next_event.voice_info:
            return None

        if self.speech_item.is_thinking != next_event.speech_item.is_thinking:
            return None

        # Combine the speech items, handling None cases
        if self.speech_item.speech is None:
            combined_speech = next_event.speech_item.speech
        elif next_event.speech_item.speech is None:
            combined_speech = self.speech_item.speech
        else:
            combined_speech = (
                f"{self.speech_item.speech} {next_event.speech_item.speech}"
            )

        return TTSEvent(
            voice_info=self.voice_info,
            speech_item=TYPES.SpeechItem(
                speech=combined_speech,
                language_code=(
                    self.speech_item.language_code
                    if self.speech_item.language_code
                    == next_event.speech_item.language_code
                    # Nothing to stop LLM from changing language part way through.
                    else "?"
                ),
                is_thinking=self.speech_item.is_thinking,
            ),
            synch_words=(
                None
                if next_event.synch_words is None
                else [
                    (t, f"{self.speech_item.speech} {subsaid}")
                    for t, subsaid in next_event.synch_words
                ]
            ),
            _finished=self._finished and next_event._finished,
        )

    def to_event_data(self):
        return TTSEventData(
            self.to_text(), self.log_color, self.voice_info, self.speech_item
        )


@dataclass(slots=True)
class SpeechRecognisedEvent(InteractionEvent):
    interaction_type: ClassVar[str] = "speech_recognised"
    event_emitter = system.world.declare_event(
        event_name="speech_recognised", data_type=InteractionEventData
    )
    speech: str
    speaker: str | None = None

    openai_role: ClassVar[Optional[str]] = "user"
    log_color: ClassVar[str] = "yellow"

    id: Optional[str] = None
    """
    Identifier from ASR node.
    Can be used to query ASR node to retrieve corresponding audio.
    """

    def to_text(self) -> Optional[str]:
        return (
            f"{self.speaker} said: {self.speech}"
            if self.speaker
            else f"User said: {self.speech}"
        )

    def to_messages(self) -> Optional[list[dict]]:

        text: str = f"<{self.speaker}>: " + self.speech if self.speaker else self.speech
        return [
            {
                "role": self.openai_role,
                "content": [{"type": "text", "text": text}],
            }
        ]


DiagnosticEvent = SpeechRecognisedEvent


@dataclass(slots=True)
class NonVerbalInteractionEvent(InteractionEvent):
    interaction_type: ClassVar[str] = "non_verbal"
    event_emitter = system.world.declare_event(
        event_name="non_verbal", data_type=InteractionEventData
    )

    description: str

    openai_role: ClassVar[Optional[str]] = "user"

    def to_text(self) -> Optional[str]:
        return self.description

    def to_messages(self) -> Optional[list[dict]]:
        return [
            {
                "role": self.openai_role,
                "content": [{"type": "text", "text": self.description}],
            }
        ]


@dataclass(slots=True)
class PersonEntryEventData:
    interaction_type = "person_entry"
    person: str


@dataclass(slots=True)
class PersonEntryEvent(InteractionEvent):
    interaction_type: ClassVar[str] = "person_entry"
    # disable event
    event_emitter = None
    # event_emitter = system.world.declare_event(
    #     event_name="person_entry",
    #     data_type=PersonEntryEventData,
    #     log_format="person entry: %(person)s",
    #     log_color="lightblue",
    # )

    person: str

    def to_text(self) -> Optional[str]:
        return None

    def __eq__(self, other):
        return (
            type(other).__name__ == self.__class__.__name__
            and other.person == self.person
        )

    def to_event_data(self):
        return PersonEntryEventData(self.person)


@dataclass(slots=True)
class PersonExitEventData:
    interaction_type = "person_exit"
    person: str


@dataclass(slots=True)
class PersonExitEvent(InteractionEvent):
    interaction_type: ClassVar[str] = "person_exit"
    # disable event
    event_emitter = None
    # event_emitter = system.world.declare_event(
    #     event_name="person_exit",
    #     data_type=PersonExitEventData,
    #     log_format="person exit: %(person)s",
    #     log_color="pink",
    # )

    person: str

    def to_text(self) -> Optional[str]:
        return None

    def __eq__(self, other):
        return (
            type(other).__name__ == self.__class__.__name__
            and other.person == self.person
        )

    def to_event_data(self):
        return PersonExitEventData(self.person)


@dataclass(slots=True)
class InteractionItem:
    event_time_s: float
    event: InteractionEvent


_history_hook_keys: tuple[str, ...] = ("ASR", "TTS", "non_verbal")


class InteractionHistory:

    _HISTORY_HOOK_REGISTRY: dict[
        Literal[_history_hook_keys],
        weakref.WeakValueDictionary[str, "InteractionHistory"],
    ] = {k: weakref.WeakValueDictionary() for k in _history_hook_keys}

    @classmethod
    def get_registered(
        cls, type: Literal[_history_hook_keys]
    ) -> list["InteractionHistory"]:
        return [v for _, v in cls._HISTORY_HOOK_REGISTRY[type].items()]

    def __init__(self) -> None:
        self._history: list[InteractionItem] = []
        self._id: str = str(uuid.uuid4())

    def __getitem__(self, idx):
        return self._history[idx]

    def __len__(self):
        return len(self._history)

    def register_hooks(self, keys: list[Literal[_history_hook_keys]]):
        for key in keys:
            self._HISTORY_HOOK_REGISTRY[key][self._id] = self

    def deregister_hooks(self, keys: list[Literal[_history_hook_keys]]):
        for key in keys:
            try:
                self._HISTORY_HOOK_REGISTRY[key].pop(self._id)
            except KeyError:
                pass

    def pop(self, index: int) -> InteractionItem:
        return self._history.pop(index)

    def to_text(self, max_len: Optional[int] = None) -> str:
        """Get history as line separated events.

        Args:
            max_len: maximum number of events to pull. If None, there is no limit. Defaults to None.

        Returns:
            The interaction history as line-separated events.
        """
        chunks: list[str] = []
        last_event: Optional[InteractionEvent] = None
        for item in reversed(self._history):  # iterate history in reverse order
            if (conflated := item.event.try_conflate(last_event)) is not None:
                chunks[-1] = conflated.to_text()
                last_event = conflated
                continue
            elif (text := item.event.to_text()) is not None:
                # Only check length when we add a new item, (so we can still conflate)
                if max_len and (len(chunks) >= max_len):
                    break
                chunks.append(text)
                last_event = item.event

        return "\n".join(reversed(chunks))

    def to_message_list(self, max_len: Optional[int] = None) -> list[dict]:
        """Get history as list of messages (for ChatCompletion API).

        Args:
            max_len: maximum number of events to pull. If None, there is no limit. Defaults to None.

        Returns:
            The interaction history as message list.
        """
        if not self._history:
            return []
        messages: list[dict] = []
        last_event: Optional[InteractionEvent] = self._history[-1].event
        for item in reversed(self._history[:-1]):  # iterate history in reverse order
            if item.event.to_messages() is None:
                continue
            # Conflate messages of the same type to avoid artifacts from streaming tts
            # We want 1 message per user.
            if (conflated := item.event.try_conflate(last_event)) is not None:
                last_event = conflated
                continue
            elif (last_event_messages := last_event.to_messages()) is not None:
                if max_len is None:
                    messages.extend(last_event_messages)
                else:
                    new_len = len(messages) + len(last_event_messages)
                    if new_len > max_len:
                        break
                    messages.extend(last_event_messages)
                    if new_len == max_len:
                        break

            last_event = item.event
        else:
            if last_event is not None:
                last_event_messages = last_event.to_messages()
                if last_event_messages is not None and (
                    not max_len or len(messages) + len(last_event_messages) <= max_len
                ):
                    messages.extend(last_event_messages)

        return messages[::-1]

    def get_person_conversation(self, person_name: str) -> Optional[str]:
        """Get conversation history since a particular person entered the scene until they left the scene.

        Args:
            person_name: the name of the person to get information about.

        Returns:
            The interaction history as line-separated events.
        """
        try:
            start_point = next(
                len(self._history) - i
                for i, item in enumerate(reversed(self._history))
                if item.event == PersonEntryEvent(person_name)
            )
        except StopIteration:
            return None

        items = []
        person_has_spoken = False
        for item in self._history[start_point:]:
            if type(item.event).__name__ == "SpeechRecognisedEvent":
                person_has_spoken = True
            if item.event == PersonExitEvent(person_name):
                break
            if (text := item.event.to_text()) is not None:
                items.append(text)
        if not person_has_spoken:
            return None
        return "\n".join(items)

    def add_to_memory(self, interaction_event: InteractionEvent, skip_emit=False):
        event_time_s = time_unix()
        if not skip_emit and interaction_event.event_emitter:
            if event_data := interaction_event.to_event_data():
                interaction_event.event_emitter.emit(event_data)
        self._history.append(InteractionItem(event_time_s, interaction_event))

    def find(
        self,
        interaction_event: type[InteractionEvent],
        att_dict: dict = {},
        reverse_order: bool = True,
    ) -> Optional[tuple[int, InteractionItem]]:
        """
        Return the first InteractionEvent that matches the type, and attribute in `att_dict`
        eg. {"function_name": "pog", "function_arguments": "max"} will only match if the attribute  `function_name` is "pog" and `function_arguments` is "max"
        """
        history = self._history if not reverse_order else reversed(self._history)
        for i, hist in enumerate(history):
            if isinstance(hist.event, interaction_event):
                original_dict = asdict(hist.event)
                sub_set = {k: original_dict[k] for k in att_dict}

                if sub_set == att_dict:
                    index = len(self._history) - i - 1 if reverse_order else i
                    return index, hist
        return None

    def reset(self):
        self._history.clear()

    def last_recognized_speech_event(self) -> Optional[SpeechRecognisedEvent]:
        for item in reversed(self._history):
            if isinstance(item.event, SpeechRecognisedEvent):
                return item.event
        return None