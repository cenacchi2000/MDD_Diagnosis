# DASS-21 Questionnaire Script with Automatic Scoring and SQLite Storage

import asyncio
import datetime
import os
import uuid

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



# Patient ID setup – use environment variable from main.py if available
def get_patient_id() -> str:
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid

DIGIT_WORDS = {"zero": "0", "one": "1", "two": "2", "three": "3"}


# Categories: d = depression, a = anxiety, s = stress
questions = [
    (1,  "I found it hard to wind down", 's'),
    (2,  "I was aware of dryness of my mouth", 'a'),
    (3,  "I couldn’t seem to experience any positive feeling at all", 'd'),
    (4,  "I experienced breathing difficulty", 'a'),
    (5,  "I found it difficult to work up the initiative to do things", 'd'),
    (6,  "I tended to over-react to situations", 's'),
    (7,  "I experienced trembling (e.g., in the hands)", 'a'),
    (8,  "I felt that I was using a lot of nervous energy", 's'),
    (9,  "I was worried about situations in which I might panic", 'a'),
    (10, "I felt that I had nothing to look forward to", 'd'),
    (11, "I found myself getting agitated", 's'),
    (12, "I found it difficult to relax", 's'),
    (13, "I felt down-hearted and blue", 'd'),
    (14, "I was intolerant of anything that kept me from getting on", 's'),
    (15, "I felt I was close to panic", 'a'),
    (16, "I was unable to become enthusiastic about anything", 'd'),
    (17, "I felt I wasn’t worth much as a person", 'd'),
    (18, "I felt that I was rather touchy", 's'),
    (19, "I was aware of the action of my heart without exertion", 'a'),
    (20, "I felt scared without any good reason", 'a'),
    (21, "I felt that life was meaningless", 'd'),
]

category_scores = {'d': 0, 'a': 0, 's': 0}


def interpret(score, category):
    score *= 2  # Multiply total by 2 as per DASS21 convention
    if category == 'd':
        if score <= 9: return score, "Normal"
        if score <= 13: return score, "Mild"
        if score <= 20: return score, "Moderate"
        if score <= 27: return score, "Severe"
        return score, "Extremely Severe"
    elif category == 'a':
        if score <= 7: return score, "Normal"
        if score <= 9: return score, "Mild"
        if score <= 14: return score, "Moderate"
        if score <= 19: return score, "Severe"
        return score, "Extremely Severe"
    elif category == 's':
        if score <= 14: return score, "Normal"
        if score <= 18: return score, "Mild"
        if score <= 25: return score, "Moderate"
        if score <= 33: return score, "Severe"
        return score, "Extremely Severe"

async def run_dass21():
    patient_id = get_patient_id()
    await robot_say("Welcome to the DASS-21 screening. Please answer 0 (Did not apply) to 3 (Most of the time).")
    for number, text, category in questions:
        await robot_say(f"Q{number}: {text}")

        while True:
            response = (await robot_listen()).lower()
            response = DIGIT_WORDS.get(response, response)
            if response in {'0', '1', '2', '3'}:
                score = int(response)
                category_scores[category] += score
                await robot_say("Thank you.")
                break
            await robot_say("Invalid. Please answer zero to three.")

        send_to_server(
            'responses_dass21',
            patient_id=patient_id,
            timestamp=datetime.datetime.now().isoformat(),
            question_number=number,
            question_text=text,
            score=score,
            category=category,
        )


    await robot_say("Thank you. Here are your scores:")
    for cat, label in [('d', 'Depression'), ('a', 'Anxiety'), ('s', 'Stress')]:
        final_score, interpretation = interpret(category_scores[cat], cat)
        await robot_say(f"{label}: {final_score} – {interpretation}")

if __name__ == "__main__":
    asyncio.run(run_dass21())
