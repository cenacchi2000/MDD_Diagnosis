# Pain Catastrophizing Scale (PCS) – Full Implementation with Scoring and DB Storage


import os
import datetime
import uuid
import asyncio

try:
    system  # type: ignore[name-defined]
except NameError:  # pragma: no cover - executed locally
    import builtins
    import importlib.util
    import inspect

    def _import_library(rel_path: str):
        caller = inspect.stack()[1].filename
        base_dir = os.path.dirname(os.path.abspath(caller))
        abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
        module_name = os.path.splitext(os.path.basename(rel_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, abs_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {abs_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    class _LocalSystem:
        import_library = staticmethod(_import_library)

    system = _LocalSystem()
    builtins.system = system

send_to_server = system.import_library("./remote_storage.py").send_to_server
speech_mod = system.import_library("./speech_utils.py")
robot_say = speech_mod.robot_say
robot_listen = speech_mod.robot_listen



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
