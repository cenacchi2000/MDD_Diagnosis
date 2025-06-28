import re
from typing import List, Optional

ROBOT_STATE = system.import_library("../../robot_state.py")
robot_state = ROBOT_STATE.state

llm_interface = system.import_library("../../lib/llm/llm_interface.py")
INTERACTION_HISTORY = system.import_library("../knowledge/interaction_history.py")


def find_matching_pattern(text: str, pattern_list: List[str]) -> Optional[str]:
    for pattern in pattern_list:
        match = re.search(r"\b" + pattern + r"\b", text)
        if match:
            return match.group()
    return None


async def determineLangCode(
    msg: str,
    interactions: Optional[INTERACTION_HISTORY.InteractionHistory] = None,
    gpt_model="gpt-4-0613",
    parent_item_id: Optional[str] = None,
) -> Optional[str]:

    context = f"Context:\n{interactions.to_message_list(10)}\n" if interactions else ""

    system_msg: str = f"""You specialize in identifying languages.

Identify the language being spoken in the last message. Respond only with the appropriate language code from the following options: {robot_state.all_languages}.
Categorize words written in English characters by their usage context, not their original language. If unsure choose English.
{context}
Only ever respond with an exact language code and no more characters.
"""

    # TODO: Use context either what is passed in or:
    # INTERACTION_HISTORY.InteractionHistory().to_message_list(10),

    messages = [
        {
            "role": "system",
            "content": system_msg,
        },
        {"role": "user", "content": msg},
    ]
    try:
        response = await llm_interface.run_chat(
            model=gpt_model,
            messages=messages,
            temperature=0,
            parent_item_id=parent_item_id,
            purpose="detect language",
        )
        reply: str = response["content"]
        result = find_matching_pattern(reply, robot_state.all_languages)
    except Exception as e:
        log.warning(f"determineLangCode Error: {e}")
        result = "eng"
    return result