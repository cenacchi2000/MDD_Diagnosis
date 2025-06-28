import re
from typing import Any, List, Callable, Optional, Awaitable

try:
    import emoji
except ImportError:
    log.warning("Failed to import `emoji`")

    class FakeEmoji:
        def replace_emoji(self, string: str, replace: str) -> str:
            return string

    emoji = FakeEmoji()


CONFIG = system.import_library("../../../Config/Chat.py").CONFIG
PERSONA_UTIL = system.import_library("../../lib/persona_util.py")
ROBOT_STATE = system.import_library("../../robot_state.py")
robot_state = ROBOT_STATE.state

BACKEND_SPECIALIZED_PRONUNCIATIONS = CONFIG["BACKEND_SPECIALIZED_PRONUNCIATIONS"]

LANG_CODE = system.import_library("./determine_tts_lang_code.py")
StreamOutput = Callable[[str, dict[str, Any]], Awaitable[Any]]


def remove_patterns(text: str, patterns: List[str]):
    for pattern in patterns:
        regexp = re.compile(pattern)
        text = re.sub(regexp, "", text)
    return text


def generate_string_cases(text: str) -> List[str]:
    cases = [text.capitalize(), text.lower(), text.upper()]
    return cases


def remap_pronunciations(
    text: str, backend_specialized_pronunciations: dict[str, dict[str, str]], lang: str
) -> str:
    voice = robot_state.get_voice_for_language(lang)

    specialized_pronunciations: dict[str, str]
    match (voice.backend):
        case "Polly" | "aws_polly_neural_v1":
            specialized_pronunciations = {
                k.lower(): v
                for k, v in backend_specialized_pronunciations.get(
                    "aws_polly_neural_v1", {}
                ).items()
            }
        case "cartesia_ai_tts_v1":
            specialized_pronunciations = {
                k.lower(): v
                for k, v in backend_specialized_pronunciations.get(
                    "cartesia_ai_tts_v1", {}
                ).items()
            }
        case _:
            return text

    if not specialized_pronunciations:
        return text

    def _replace_pronunciations(match: re.Match[str]) -> str:
        word = match.group(0).lower()
        replacement = specialized_pronunciations.get(word, match.group(0))
        return replacement

    pattern = "|".join(map(re.escape, specialized_pronunciations.keys()))
    return re.sub(pattern, _replace_pronunciations, text, flags=re.IGNORECASE)


async def dummyStream(msg: str, kwargs: dict[str, Any] = {}):
    pass


_onlyPunctuation = re.compile(r"[\.\-_()\[\]{}\*\?! '\"]+")


async def streamToTTS(msg: Optional[str], kwargs: dict[str, Any] = {}):
    if not msg:
        log.warning("streamToTTS: ignoring empty massage")
        return

    # Filter robot name from message
    robot_name_colon = [
        n + ":" for n in generate_string_cases(PERSONA_UTIL.get_robot_name())
    ]
    filtered_msg: str = remove_patterns(msg, robot_name_colon)

    # Filter out emojis
    filtered_msg = emoji.replace_emoji(filtered_msg, "")

    # Detect language
    parent_item_id = kwargs.get("parent_item_id", None)
    lang_detected = kwargs.get("lang_code", None)
    if lang_detected is None:
        interaction = kwargs.get("interaction", None)
        lang_detected = await LANG_CODE.determineLangCode(
            filtered_msg,
            interaction,
            parent_item_id=parent_item_id,
        )
    if lang_detected not in robot_state.all_languages:
        match lang_detected:
            # Handle lang code mismatch
            case "nor" | "nob" | "nno":
                if "nob" in robot_state.all_languages:
                    lang_detected = "nob"  # polly
                elif "nno" in robot_state.all_languages:
                    lang_detected = "nno"  # OAI
                else:
                    log.warning(
                        f"streamToTTS: robot does not currently support language: {lang_detected}. Defaulting to English."
                    )
                    lang_detected = "eng"
            case _:
                log.warning(
                    f"streamToTTS: robot does not currently support language: {lang_detected}. Defaulting to English."
                )
                lang_detected = "eng"

    # Remap pronunciations
    filtered_msg: str = remap_pronunciations(
        filtered_msg, BACKEND_SPECIALIZED_PRONUNCIATIONS, lang_detected
    )

    # It's possible to end up with the last token in a response being unvocalizable.
    if not _onlyPunctuation.fullmatch(filtered_msg) and filtered_msg:
        system.messaging.post(
            "tts_say",
            {
                "message": filtered_msg,
                "language_code": lang_detected,
                "parent_item_id": parent_item_id,
            },
        )