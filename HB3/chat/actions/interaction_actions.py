"""Actions for interacting with people."""

import os
import re
import html
import asyncio
from typing import List, Literal, Optional

import aiohttp

STATIC_CONFIG = system.import_library("../../../Config/Static.py")
INTERACTION_HISTORY = system.import_library("../knowledge/interaction_history.py")
ROBOT_STATE = system.import_library("../../robot_state.py")
robot_state = ROBOT_STATE.state

TYPES = system.import_library("../../lib/types.py")

voice_cloning = system.import_library("../../lib/voice_cloning.py")

stream_module = system.import_library("../lib/stream_outputs.py")


CyclingShuffleIterator = system.import_library(
    "../../lib/cycling_shuffle_iterator.py"
).CyclingShuffleIterator

ACTION_UTIL = system.import_library("./action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry
ActionBuilder = ACTION_UTIL.ActionBuilder
Action = ACTION_UTIL.Action
PARENT_ITEM_ID = ACTION_UTIL.PARENT_ITEM_ID


@ActionRegistry.register_builder
class GetConversationalTopic(ActionBuilder):
    def __init__(self, use_topic_fallback: bool = False) -> None:
        self.use_topic_fallback = use_topic_fallback
        self.reset()

    def reset(self) -> None:
        self.last_topic_list: list[str] = []
        self.iteration_compleat: bool = False
        self.topic_iterator = CyclingShuffleIterator(
            self.last_topic_list, self._compleat_iteration_cb
        )

    async def _topic_fallback(self) -> str:
        # """curl https://uselessfacts.jsph.pl/api/v2/facts/random"""
        # url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
        # headers = {"Accept": "application/json"}
        # timeout = aiohttp.ClientTimeout(total=1)  # Timeout value in seconds

        # async with aiohttp.ClientSession(timeout=timeout) as session:
        #     try:
        #         async with session.get(url, headers=headers) as response:
        #             data = await response.json()
        #             if response.status == 200:
        #                 return _sanitize_string(data["text"])
        #             else:
        #                 return f"Failed to retrieve topic HTTP status code: {response.status}"

        #     except asyncio.TimeoutError:
        #         return "Failed to retrieve topic: response timeout"
        return "Failed to retrieve topic: no fallback"

    def _compleat_iteration_cb(self) -> None:
        self.iteration_compleat = True

    def factory(self) -> list[Action]:
        active_topic_list: list[str] | None = (
            system.persona_manager.current_persona.topics
        )
        topic_changed: bool = active_topic_list != self.last_topic_list
        if topic_changed:
            self.last_topic_list = (
                active_topic_list.copy() if active_topic_list is not None else []
            )
            self.iteration_compleat = False
            self.topic_iterator = CyclingShuffleIterator(
                self.last_topic_list, self._compleat_iteration_cb
            )
        if not self.last_topic_list and not self.use_topic_fallback:
            return []

        async def get_conversational_topic() -> str:
            """You must use this when deciding what topic to talk about.
            Use this as a starting point for an interesting conversation.
            Call this often instead of asking open ended questions,
            you must take control of the conversation.
            #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
            """
            try:
                rval: str | None = next(self.topic_iterator)
                rval = (
                    await self._topic_fallback()
                    if (self.use_topic_fallback and self.iteration_compleat)
                    or (self.use_topic_fallback and rval is None)
                    else rval
                )
            except Exception:
                rval = None
            rval = rval if rval else "Failed to retrieve topic"
            return rval

        return [get_conversational_topic]


@ActionRegistry.register_builder
class SelectVoice(ActionBuilder):
    def factory(self) -> list[Action]:
        # No voices to choose from...
        if not robot_state.available_tts_voices:
            log.warning("No voices to choose from in select_voice_factory")
            return []

        voice_info_dict: dict[str, dict] = {
            info.name: info
            for info in robot_state.available_tts_voices
            # Polly voices are monolingual therefore we can't really switch
            if info.engine == "Service Proxy" and info.backend != "aws_polly_neural_v1"
        }

        # Get the filter list from persona
        filter_list: list[str] = [
            alt_voice.name
            for alt_voice in system.persona_manager.current_persona.alternate_voices
        ]
        # Filter voice_info_dict to only include voices that exist in both the dict and the filter list
        voice_info_dict = {
            name: info
            for name, info in voice_info_dict.items()
            if info.name in filter_list
        }

        # Filter out voices that are not available in the current language
        # TODO: Decide what is the best way to do this SI-334
        # languages from persona (languages that robot should be able to speak in)
        # filter_languages: set[str] = set(
        #     [
        #         default_voice.language_code
        #         for default_voice in system.persona_manager.current_persona.default_voice
        #     ]
        # )

        # This checks that the voices can do ALL languages that are in the persona
        # voice_info_dict = {
        #     name: info
        #     for name, info in voice_info_dict.items()
        #     if info.languages is None
        #     or all(lang in info.languages for lang in filter_languages)
        # }

        # If we don't have any multilingual voices available we don't want to switch.
        if not voice_info_dict:
            return []

        # add default to the voice list
        voice_info_dict["default"] = None

        clone_info = voice_cloning.get_voice_cloning_info()
        if not clone_info.error or clone_info.retry:
            voice_info_dict["user"] = None
            user_docstring = """
    Select `user` for user voice, when people say things like:
    `use my voice`, `clone my voice`, `copy my voice` or `talk like me`.
    Allow to select `user` voice even if it is already selected in order to
    clone voice continuously to capture the latest intonation."""
        else:
            user_docstring = ""

        voice_list = tuple(voice_info_dict.keys())

        async def select_voice(speaker: Literal[voice_list]) -> str:

            # play long thinking sound
            system.messaging.post(
                "tts_say",
                {
                    "message": "",
                    "language_code": robot_state.last_language_code,
                    "is_thinking": "long",
                    "parent_item_id": PARENT_ITEM_ID.get(),
                },
            )

            try:
                if speaker == "default":
                    log.info("Switching to default voice")
                    robot_state.reset_to_default_voice()
                elif speaker == "user":
                    if clone_info.error:
                        return f"ERROR (please retry): {clone_info.error}"
                    log.info("Cloning speaker voice...")
                    voice = await voice_cloning.clone_user_voice(clone_info)
                    robot_state.activate_alternate_tts_voice(voice)
                else:
                    voice = voice_info_dict[speaker]
                    log.info(f"Switching to voice: {voice}")
                    robot_state.activate_alternate_tts_voice(voice)

            except Exception:
                log.exception(f"Switching voice to '{speaker}' failed")
                raise RuntimeError(f"Switching voice to '{speaker}' failed")
            return f"`{speaker}` active"

        select_voice.__doc__ = f"""Select the voice that will be used when speaking to the user.
    Select `default` for the default voice, when people say things like:
    `go back to your normal voice` or `do your ordinary voice`.{user_docstring}

    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
    Args:
        speaker (str): name of the speaker to use
    """

        return [select_voice]


def _search_animations(animation_search_path: str) -> tuple[str, ...] | None:
    try:
        projects: List[str] = next(
            os.walk(STATIC_CONFIG.BASE_CONTENT_PATH + animation_search_path)
        )[1]
    except StopIteration:
        return None
    expression_sequences = tuple(projects)
    if len(projects) == 0:
        return None
    return expression_sequences


def _play_animation(animation_search_path: str, animation: str):
    robot_state.set_thinking(False)
    system.messaging.post("play_sequence", animation_search_path + "/" + animation)
    return f"played {animation}"


@ActionRegistry.register_builder
class ShowFacialExpression(ActionBuilder):

    animation_search_path: str = "Animations.dir/System.dir/Chat Expressions.dir"

    def factory(self) -> list[Action]:
        """A factory to generate the show_facial_expression function."""

        expression_sequences = _search_animations(self.animation_search_path)

        if expression_sequences is None:
            return []

        async def show_facial_expression(
            expression: Literal[expression_sequences],
        ) -> str:
            """Show facial expression. Use when requested. Note that the number in the name denotes the intensity of the expression.
            Args:
                expression (str): the facial expression to show.
            """

            return _play_animation(self.animation_search_path, expression)

        return [show_facial_expression]


@ActionRegistry.register_builder
class ShowGesture(ActionBuilder):

    animation_search_path: str = "Animations.dir/System.dir/Chat Gesture.dir"

    def factory(self) -> list[Action]:
        """A factory to generate the show_facial_expression function."""
        gesture_sequences = _search_animations(self.animation_search_path)

        if gesture_sequences is None:
            return []

        async def show_gesture(
            gesture: Literal[gesture_sequences],
        ) -> Optional[str]:
            """Show gesture. Gestures should be used appropriately, such as waving when someone is saying goodbye.
            Note that if there is a number in the name it denotes the intensity of the gesture.
            #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
            Args:
                gesture (str): the gesture to show.
            """

            if not gesture:
                return
            return _play_animation(self.animation_search_path, gesture)

        return [show_gesture]


@ActionRegistry.register_builder
class StopTalking(ActionBuilder):

    animation_search_paths: list[str] = [
        "Animations.dir/System.dir/Chat Gesture.dir",
        "Animations.dir/System.dir/Chat Expressions.dir",
    ]

    def factory(self) -> list[Action]:

        search_path_animations = {}
        animation_list = tuple()
        for search_path in self.animation_search_paths:
            if animations := _search_animations(search_path):
                search_path_animations[search_path] = animations
                animation_list = animations + animation_list

        if not animation_list:
            return []

        async def interrupt_go_silent(
            animation: Literal[animation_list],
        ) -> str:
            """
            If you recieved a message like 'stop talking', 'be quiet' or 'shut up' you must stop speaking and select an animation to reflecting your mood from the user input.
            Only trigger this function when the user message is explicitly telling you to be quiet and not speak.
            DO NOT call this function for anything else.
            Args:
                animation (str): the animation to show.
            """
            system.messaging.post("tts_stop", True)
            # Clear any response tasks as well
            if robot_state.response_task:
                robot_state.cancel_response_task()

            if not animation:
                return "conversation stopped but no animation played"

            for search_path in search_path_animations.keys():
                if animation in search_path_animations[search_path]:
                    return "conversation stopped, and " + _play_animation(
                        search_path, animation
                    )

            return "stopped conversation"

        return [interrupt_go_silent]


@ActionRegistry.register_action
async def do_joke():
    """Get a generic joke, This joke can serve as a template when a specific joke is requested.
    Note that the joke is in english, and it might not translate well into other languages.
    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
    """

    url = "https://icanhazdadjoke.com/"
    headers = {"Accept": "application/json"}
    timeout = aiohttp.ClientTimeout(total=1)  # Timeout value in seconds

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                if response.status == 200:
                    return _sanitize_string(data["joke"])
                else:
                    raise Exception(
                        "Failed to retrieve template joke, you will have to improvise."
                    )
        except asyncio.TimeoutError:
            raise Exception(
                "Failed to retrieve template joke, you will have to improvise."
            )


def _sanitize_string(s: str) -> str:
    """Sanitizes a string, removing various unwanted characters and patterns, and escaping necessary characters."""
    s = s.strip()  # Removing leading and trailing whitespace
    s = re.sub(r"\s+", " ", s)  # Removing extra spaces between words
    s = re.sub(r"<[^>]*>", "", s)  # Removing HTML tags
    s = re.sub(
        r"<script[^>]*>.*?</script>", "", s, flags=re.DOTALL
    )  # Removing JavaScript code
    s = re.sub(
        r"[^\w\s,.\-?!]", "", s
    )  # Removing special characters (except some common punctuation)
    s = html.escape(s)  # Escaping HTML characters to prevent XSS
    s = s.replace(
        "'", "''"
    )  # Escaping SQL-specific characters to prevent SQL Injection
    s = re.sub(
        r"[\x00-\x1f\x7f-\x9f]", "", s
    )  # Removing control characters and non-printable characters
    return s