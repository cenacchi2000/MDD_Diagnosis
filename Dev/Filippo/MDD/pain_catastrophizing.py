# Pain Catastrophizing Scale (PCS) – Full Implementation with Scoring and DB Storage

import os
import sys

sys.path.append(os.path.dirname(__file__))
from remote_storage import send_to_server


async def robot_say(text: str) -> None:
    """Speak through Ameca with console fallback."""
    print(f"[Ameca]: {text}")
    try:
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass


async def robot_listen() -> str:
    """Return the next spoken utterance."""
    try:
        evt = await system.wait_for_event("speech_recognized")
        if isinstance(evt, dict):
            return evt.get("text", "").strip()
    except Exception:
        pass
    return ""

import datetime
import uuid
import asyncio



# Patient ID handling
def get_patient_id() -> str:
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid

# PCS questions
pcs_questions = [
    "I worry all the time about whether the pain will end.",
    "I feel I can’t go on.",
    "It’s terrible and I think it’s never going to get any better.",
    "It’s awful and I feel that it overwhelms me.",
    "I feel I can’t stand it anymore.",
    "I become afraid that the pain will get worse.",
    "I keep thinking of other painful events.",
    "I anxiously want the pain to go away.",
    "I can’t seem to keep it out of my mind.",
    "I keep thinking about how much it hurts.",
    "I keep thinking about how badly I want the pain to stop.",
    "There’s nothing I can do to reduce the intensity of the pain.",
    "I wonder whether something serious may happen."
]

rating_scale = {
    "0": "Not at all",
    "1": "To a slight degree",
    "2": "To a moderate degree",
    "3": "To a great degree",
    "4": "All the time"
}

def current_timestamp():
    return datetime.datetime.now().isoformat()

DIGIT_WORDS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4"}


async def run_pcs():
    patient_id = get_patient_id()
    total_score = 0
    await robot_say("Welcome to the Pain Catastrophizing Scale questionnaire. Please answer each item based on how you feel when you're in pain.")
    await robot_say("The scale is: 0 = Not at all, 1 = Slight degree, 2 = Moderate degree, 3 = Great degree, 4 = All the time.")

    for i, question in enumerate(pcs_questions):
        await robot_say(f"Q{i+1}: {question}")

        while True:
            response = (await robot_listen()).lower()
            response = DIGIT_WORDS.get(response, response)
            if response in rating_scale:
                score = int(response)
                await robot_say("Thank you.")
                break
            await robot_say("Invalid response. Please answer zero to four.")

        total_score += score
        send_to_server(
            'responses_pcs',
            patient_id=patient_id,
            timestamp=current_timestamp(),
            question_number=i + 1,
            question_text=question,
            score=score,
        )

        await robot_say(f"Recorded response: {rating_scale[response]} (Score: {score})")

    await robot_say(f"\nThank you. Your total PCS score is {total_score}.")
    if total_score >= 30:
        await robot_say("This indicates a clinically relevant level of pain catastrophizing.")
    else:
        await robot_say("Your score suggests a lower tendency toward pain catastrophizing.")

if __name__ == "__main__":
    asyncio.run(run_pcs())
