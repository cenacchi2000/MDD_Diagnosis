import os
import json
from typing import List, Optional
from dataclasses import dataclass

import aiohttp

CONFIG = system.import_library("../../Config/Static.py")
BASE_CONTENT_PATH = CONFIG.BASE_CONTENT_PATH
ANIMATION_BASE_PATHS: List[str] = [
    "MOTF Content.dir/Revision - 04052022.dir/",
    "MOTF Content.dir/Added - 20220721.dir/",
    "MOTF Content.dir/Chatbot Gestures (important names).dir/",
]


@dataclass
class RulesBasedSpeech:
    speech: str
    rule: str
    animation_path: Optional[str] = None


class RulesBasedChatbot:
    def __init__(self, url: Optional[str]) -> None:
        if url is None:
            raise ValueError("url must not be None, check RULES_BASED_CHATBOT_URL")
        self._url = url
        self._seprator = " - "
        self._animation_map: dict[str, str] = self._build_map()
        self._animation_map_exact: dict[str, str] = self._build_map(True)

    def _get_rule(self, file_name: str) -> str:
        index = file_name.find(self._seprator)
        return file_name[:index] if index != -1 else ""

    def _build_map(self, exact=False) -> dict[str, str]:
        result: dict[str, str] = {}
        for animation_path in ANIMATION_BASE_PATHS:
            if not os.path.isdir(BASE_CONTENT_PATH + animation_path):
                raise FileExistsError(
                    f"Could not find {BASE_CONTENT_PATH + animation_path}"
                )
            animations: List[str] = next(os.walk(BASE_CONTENT_PATH + animation_path))[1]
            if exact:
                # Some of the MOTF script has sequence names like "motf - smile", we
                # need to make sure those match even though the prefix is generic and
                # the suffix is the matcher. We just match the entire response to a
                # sequence name.
                result.update(
                    {
                        anim.rsplit(".", 1)[0]: animation_path + anim
                        for anim in animations
                    }
                )
            else:
                # The rules scripts are setup to have an identifier followed by the text
                # in each response. The identifier can be used to match to a
                # pre-animated or pre-recorded response. e.g. "12.3.1 - Hello human"
                result.update(
                    {self._get_rule(anim): animation_path + anim for anim in animations}
                )
        result.pop("", None)
        return result

    def _extract_message(self, msg: str) -> Optional[RulesBasedSpeech]:
        index = msg.find(self._seprator)
        if index == -1:
            return
        speech: str = msg[index + len(self._seprator) :]
        rule: str = msg[:index]
        animation_path: Optional[str] = self._animation_map.get(rule)
        animation_path_exact: Optional[str] = self._animation_map_exact.get(msg)
        return RulesBasedSpeech(speech, rule, animation_path_exact or animation_path)

    async def call_rules_based_chatbot(self, msg: str) -> List[RulesBasedSpeech]:
        async with aiohttp.ClientSession() as session:
            async with session.post(self._url, json={"message": msg}) as response:
                data: str = await response.text()
                d = json.loads(data)
                speech_with_rule: List[str] = d["message"]
                result: List[RulesBasedSpeech] = []
                for s in speech_with_rule:
                    if speech := self._extract_message(s):
                        result.append(speech)
                    else:
                        log.warning(f"Invalid RulesBasedChatbot message: {s}")
                return result