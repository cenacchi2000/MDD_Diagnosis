from typing import List, Literal
from collections import defaultdict

from tritium.ai.personas.persona import SingleLanguageVoice

TYPES = system.import_library("./types.py")


def _convert_persona_default_voice_to_language_voice_map(
    default_voice: List[SingleLanguageVoice],
) -> dict[str, TYPES.TTSVoiceInfo]:
    """
    Converts the default voice of a persona to a language voice map.
    """
    language_voice_map: dict[str, TYPES.TTSVoiceInfo] = {}
    for default_voice_entry in default_voice:
        language_voice_map[default_voice_entry.language_code] = TYPES.TTSVoiceInfo(
            name=default_voice_entry.name,
            engine=default_voice_entry.engine
            or "Service Proxy",  # Optional, if None, use Service Proxy
            backend=default_voice_entry.backend,
        )
    return language_voice_map


def get_llm_persona_info(
    use_for: Literal["chat", "vision"] = "chat"
) -> tuple[str, str, dict, str, dict[str, TYPES.TTSVoiceInfo]]:
    """Return tuple(system_message, llm_model, llm_backend_params, robot_name, language_voice_map) from active persona"""

    persona_prompt: str = ""
    robot_name: str = "<unnamed robot>"
    llm_model: str = "gpt-4o"
    llm_backend_params: dict = {}
    language_voice_map: dict[str, TYPES.TTSVoiceInfo] = {}
    if (persona := system.persona_manager.current_persona) is not None:

        robot_name = persona.robot_name

        try:
            still_default: bool = True
            for backend in persona.backends:

                # Skip backend if it's not used for the current use case
                if use_for not in backend.used_for:
                    continue
                still_default = False
                llm_model = backend.model
                llm_backend_params = {
                    param.name: param.value for param in backend.parameters
                }

                language_voice_map = (
                    _convert_persona_default_voice_to_language_voice_map(
                        persona.default_voice
                    )
                )

            if still_default:
                raise RuntimeError()

        except Exception:
            log.exception("Error getting persona backend info")
            log.warning(
                f"get_llm_persona_info(): Falling back to use `{llm_model}` as the LLM model, and `{llm_backend_params} parameters`"
            )

        persona_prompt += "\n".join([p.value for p in persona.personality.prompts])

        needs_robot_name = "{ROBOT_NAME}" not in persona_prompt
        needs_location = "{LOCATION}" not in persona_prompt and persona.location
        needs_activity = "{ACTIVITY}" not in persona_prompt and persona.activity

        if needs_robot_name:
            persona_prompt = "\n".join(
                [f"You are a robot called `{robot_name}`", persona_prompt]
            )
        if needs_location:
            persona_prompt = "\n".join(
                [f"About your Location:\n{persona.location}", persona_prompt]
            )
        if needs_activity:
            persona_prompt = "\n".join(
                [
                    f"About the activity you are currently engaging in:\n{persona.activity}",
                    persona_prompt,
                ]
            )

        # Do a single format_map call with all replacements, as format_map removes all placeholders, even if they don't match
        format_mapping = defaultdict(
            str,
            ROBOT_NAME=robot_name,
            LOCATION=persona.location if persona.location else "",
            ACTIVITY=persona.activity if persona.activity else "",
        )
        persona_prompt = persona_prompt.format_map(format_mapping)

    else:
        log.error(
            f"get_llm_persona_info(): No persona set, system_message will be empty and falling back to use `{llm_model}` as the LLM model"
        )

    return persona_prompt, llm_model, llm_backend_params, robot_name, language_voice_map


def get_robot_name() -> str:
    """
    Gets the robot name from the current persona.
    Note that it defaults to "Ameca" if no persona is currently set
    to avoid having to handle no persona every time we want to get the robot name.
    """
    if (persona := system.persona_manager.current_persona) is not None:
        return persona.robot_name
    log.warning("No persona set, defaulting to 'Ameca'")
    return "Ameca"


def get_language_voice_map() -> dict[str, TYPES.TTSVoiceInfo]:
    """
    Gets the language voice map from the current persona.
    """
    if (persona := system.persona_manager.current_persona) is not None:
        return _convert_persona_default_voice_to_language_voice_map(
            persona.default_voice
        )
    log.warning("No persona set, and therefore no language voice map available")
    return {}