"""System level actions."""

import re
import asyncio
from typing import Any, Literal
from dataclasses import asdict

import aiohttp
from tritium.config import Protocol, get_service_config
from tritium.exceptions import TritiumConfigError

VOICE_ID_UTIL = system.import_library("../../Perception/lib/voice_id_util.py")

ACTION_UTIL = system.import_library("./action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry
ActionBuilder = ACTION_UTIL.ActionBuilder
Action = ACTION_UTIL.Action
PARENT_ITEM_ID = ACTION_UTIL.PARENT_ITEM_ID

RAGResources = system.import_library("../../robot_state/RAGCollectionInfo.py")


# We use "pactl" which is a commandline client for pulseaudio to inspect and change
# audio device configuration.
async def _change_volume(change):
    MIN_VOLUME = 10
    MAX_VOLUME = 90
    current_volume = await _get_volume()
    target_volume = current_volume + change
    result = f"Volume changed from {current_volume} to {target_volume}"
    if target_volume >= MAX_VOLUME:
        target_volume = MAX_VOLUME
        result = f"Volume changed from {current_volume} to {target_volume} (at max)"
    elif target_volume <= MIN_VOLUME:
        target_volume = MIN_VOLUME
        result = f"Volume changed from {current_volume} to {target_volume} (at min)"
    await _run_pactl(
        "set-sink-volume", "@DEFAULT_SINK@", str((target_volume * 65536 // 100))
    )
    return result


async def _get_volume():
    process = await _run_pactl("get-sink-volume", "@DEFAULT_SINK@")
    stdout_text = await process.stdout.read(4096)
    print(stdout_text.decode())
    match = re.search(r"^.+front-left: (\d+) /", stdout_text.decode())
    return round((float(match[1]) / 65536) * 100)


async def _run_pactl(*args):
    process = await asyncio.create_subprocess_exec(
        "pactl",
        *args,
        env={"PULSE_RUNTIME_PATH": "/tmp/pulseaudio"},
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    await process.wait()
    if process.returncode != 0:
        err_text = await process.stderr.read(4096)
        log.error("pactl failed!", err_text)
        raise Exception(err_text)
    return process


@ActionRegistry.register_builder
class SearchKnowledgeBase(ActionBuilder):
    def __init__(self):
        self._service_config_query: Any | None
        try:
            self._service_config_query = get_service_config(
                Protocol.HTTP, "api/v1/rag/query", "service_proxy_llm", True
            )[0]
            self._headers = {
                "Accept": "application/json",
                "x-tritium-system-uuid": self._service_config_query.identifier,
                "x-tritium-system-token": self._service_config_query.token,
            }
        except TritiumConfigError:
            log.warning(
                f"Unable to fetch knowledge base credentials, `{self.get_action_id()}` disabled"
            )
            self._service_config_query = None
            self._headers = {}
        self._timeout = aiohttp.ClientTimeout(total=3)

    def factory(self) -> list[Action]:

        _collections_info: list[dict] = asdict(
            RAGResources.RAGCollectionInfoList.get()
        ).get("rag_collection", [])
        if self._service_config_query is None or not _collections_info:
            return []

        def _wrapper(
            collection_id: str, collection_name: str, description: str
        ) -> Action:

            action_name: str = (
                f"search_{collection_name.replace(' ', '_').lower()}_knowledge_base"
            )

            async def search_knowledge_base(search_phrase: str):
                log.info(
                    f"Searching collection with id `{collection_id} for phrase: {search_phrase}"
                )
                url = self._service_config_query.url
                async with aiohttp.ClientSession(timeout=self._timeout) as session:
                    try:
                        async with session.post(
                            url,
                            headers=self._headers,
                            json={
                                "collection_id": collection_id,
                                "query": search_phrase,
                                "parent_item_id": PARENT_ITEM_ID.get(),
                            },
                        ) as response:
                            text = await response.text()
                            if response.status == 200:
                                return text
                            else:
                                log.warning(f"{action_name} Failed: {text}")
                                raise RuntimeError(
                                    "Search Failed: knowledge base internal error"
                                )
                    except asyncio.TimeoutError:
                        raise RuntimeError(
                            "Search Failed, knowledge base not responding."
                        )

            search_knowledge_base.__name__ = action_name
            search_knowledge_base.__doc__ = f"""Search for accurate information in knowledge base.
                {description}
                Use this action when the topic being discussed is even vaguely related.
                #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
                Args:
                    search_phrase: search phrase or search terms to use
                """
            return search_knowledge_base

        return [
            _wrapper(
                info["collection_id"], info["collection_name"], info["description"]
            )
            for info in _collections_info
        ]


@ActionRegistry.register_builder
class RememberVoiceWithName(ActionBuilder):
    def factory(self) -> list[Action]:
        self._voice_id = system.unstable.stash.get_local(
            "/profile/nodes/speech_recognition/config/service_proxy_config/voice_id",
            default=False,
            required=False,
        )

        if not self._voice_id:
            return []

        async def remember_voice_with_name(speaker_name: str):
            if speaker_name == VOICE_ID_UTIL.UNKNOWN_SPEAKER_TOKEN:
                return f"Failed: {speaker_name} is not a valid speaker name, acquire the name of the speaker and try again"
            if (voice_id := VOICE_ID_UTIL.get_voice_id_head()) is None:
                return "Failed: Unable to match voice"

            VOICE_ID_UTIL.update_know_voice(speaker_name, voice_id)
            return f"{speaker_name}'s voice was successfully updated"

        remember_voice_with_name.__doc__ = """
        Remember the voice of the current speaker, and store it in memory, so you can recognize them later.
        Use this when someone introduces themselves or asks you to remember them.
        Also use this if they ask you if you remember them, but they provide a name and are currently an unindentified speaker.
        You can remember and recognize multiple voices at the same time, and you can call this at any time.
        #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
        Args:
            speaker_name (str): name of the speaker
        """

        # Note: the "Also use this if they ask you if you remember them, but they provide a name and are currently an unindentified speaker."
        # is done because it is quite common for people to ask "Can you remember me? My voice is <name>" when they want to be remembered
        # And the LLM might misinterpret it as just a question about if it remembers them, rather than a request to remember them.

        recognized_speakers = tuple(VOICE_ID_UTIL.get_known_voices())
        if not recognized_speakers:
            return [remember_voice_with_name]

        async def forget_voice_by_name(speaker_name: Literal[recognized_speakers]):
            """
            Remove the voice of speaker from memory.
            If the requested name does not match any known voices,
            confirm with the user which speaker_name to remove.
            Suggest one if you think there is one similar in the list.
            #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
            Args:
                speaker_name (str): name of the speaker
            """
            try:
                VOICE_ID_UTIL.remove_voice(speaker_name)
            except RuntimeError:
                # Let llm know `speaker_name` is invalid
                raise
            except Exception:
                # Hide detail of other error from llm
                raise RuntimeError(
                    f"Unexpected error occured when trying to remove voice of `{speaker_name}`"
                )

            return f"{speaker_name}'s voice was successfully removed"

        return [remember_voice_with_name, forget_voice_by_name]


##################### TODO convert all volume actions into a single action builder  #############################


@ActionRegistry.register_action
async def turn_volume_up():
    """Turn up your volume.
    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS

    """
    try:
        return await _change_volume(10)
    except Exception:
        log.exception("changing volume", warning=True)
        return "error executing volume change"


@ActionRegistry.register_action
async def turn_volume_down():
    """Turn down your volume.
    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS

    """
    try:
        return await _change_volume(-10)
    except Exception:
        log.exception("changing volume", warning=True)
        return "error executing volume change"


@ActionRegistry.register_action
async def change_head_colour(colour: list[float]):
    """Change the colour of your head.

    You can only change to a single rgb value at a time. If you want to change it to another colour after you will get a chance to call this function again.

    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS

    Args:
        colour: the colour to change your head to. This MUST be in the format (r, g, b) where r, g, b represent the colour intensities for red, green, blue. Each value MUST be between 0 and 1, with 0 indicating 0 intensity and 1 indicating full intensity of that colour.
    """
    system.messaging.post("set_led", tuple(colour))
    return f"Set LED Colors to {colour}"


@ActionRegistry.register_action
async def enable_camera_tracking():
    """Enable `camera_tracking`. Where users will be taking photos of you, and you will smile for the camera.
    You will automatically disable camera_tracking, so you can call this function multiple times.
    The following commands are often related to this function:
    Any request for a picture, photo or selfie, `Smile for the camera`, `Say cheese`.
    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS

    """
    system.messaging.post("camera_tracking", True)
    return "Camera tracking enabled"


class ChangeModeOfOperation(ActionBuilder):
    def __init__(self, modes: list[str]):
        self.modes: tuple[str] = tuple(modes)

    def factory(self) -> list[Action]:
        if not self.modes:
            return []

        async def change_mode_of_operation(mode: Literal[self.modes]):
            """Change the mode of operation, and enters the mode specified
            Args:
                mode (str): Mode of operation to switch to.
            """
            system.messaging.post("mode_change", mode)
            return f"Entering {mode} mode"

        return [change_mode_of_operation]


@ActionRegistry.register_action
async def get_robot_serial():
    """
    When you are asked for your serial number, tell the user the serial number of your system.
    When saying your serial number, say each letter individually, then ignore all zeros before the first number in the numerical part of your serial number and you must say the remaining numbers together as one number.
    #REQUIRES_SUBSEQUENT_FUNCTION_CALLS
    """
    try:
        serial_number: str = await system.unstable.stash.get("/serial")

        return f"Serial number found: {serial_number}"
    except asyncio.TimeoutError:
        raise Exception("Failed to retrieve serial")