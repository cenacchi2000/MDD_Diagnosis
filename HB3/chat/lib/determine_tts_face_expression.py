import os
import re
from typing import List, Optional

STATIC_CONFIG = system.import_library("../../../Config/Static.py")
CONFIG = system.import_library("../../../Config/Chat.py").CONFIG

llm_interface = system.import_library("../../lib/llm/llm_interface.py")
INTERACTION_HISTORY = system.import_library("../knowledge/interaction_history.py")


def find_matching_pattern(text: str, pattern_list: List[str]) -> Optional[str]:
    for pattern in pattern_list:
        match = re.search(r"\b" + pattern + r"\b", text)
        if match:
            return match.group()
    return None


class TTSFaceExpression:

    @classmethod
    def from_animation_dir(
        cls, animation_search_path: str, default_expression: Optional[str] = None
    ) -> "TTSFaceExpression":
        expressions: list[str] = next(
            os.walk(STATIC_CONFIG.BASE_CONTENT_PATH + animation_search_path)
        )[1]

        # remove extension
        expressions = [os.path.splitext(p)[0] for p in expressions]
        if not expressions:
            raise RuntimeError(
                f"No animations found in: {STATIC_CONFIG.BASE_CONTENT_PATH + animation_search_path}"
            )
        return cls(expressions, default_expression)

    def __init__(
        self, expressions: list[str], default_expression: Optional[str] = None
    ):
        self.expressions = expressions
        self.default: str = (
            default_expression
            if default_expression is not None
            else self.expressions[0]
        )
        if self.default not in self.expressions:
            self.expressions = [default_expression] + self.expressions

    async def determine_tts_face_expression(
        self,
        msg: str,
        interactions: Optional[INTERACTION_HISTORY.InteractionHistory] = None,
        gpt_model="gpt-4o-mini",
        parent_item_id: Optional[str] = None,
    ) -> Optional[str]:

        context = f"Context:\n{interactions.to_text(10)}\n" if interactions else ""

        system_msg = f"""You specialize in facial expressions, and sentiment analysis.

Match the facial expression that is the most appropriate to the text based on the sentiment that it conveys.
Respond only with the appropriate facial expression from the following options: {self.expressions}
Note that the the number at the end denotes the intensity of the expression.
{context}
Only ever respond with an exact facial expressions and no more characters.
"""
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
                purpose="facial expression",
            )
            reply: str = response["content"] if response is not None else ""
            result = find_matching_pattern(reply, self.expressions)

        except Exception:
            log.exception("determine_tts_face_expression Error")
            result = self.default

        return result