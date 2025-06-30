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

# EQ-5D-5L dimension descriptions
eq5d5l_dimensions = {
    "Mobility": [
        "I have no problems in walking about",
        "I have slight problems in walking about",
        "I have moderate problems in walking about",
        "I have severe problems in walking about",
        "I am unable to walk about",
    ],
    "Self-Care": [
        "I have no problems washing or dressing myself",
        "I have slight problems washing or dressing myself",
        "I have moderate problems washing or dressing myself",
        "I have severe problems washing or dressing myself",
        "I am unable to wash or dress myself",
    ],
    "Usual Activities": [
        "I have no problems doing my usual activities",
        "I have slight problems doing my usual activities",
        "I have moderate problems doing my usual activities",
        "I have severe problems doing my usual activities",
        "I am unable to do my usual activities",
    ],
    "Pain/Discomfort": [
        "I have no pain or discomfort",
        "I have slight pain or discomfort",
        "I have moderate pain or discomfort",
        "I have severe pain or discomfort",
        "I have extreme pain or discomfort",
    ],
    "Anxiety/Depression": [
        "I am not anxious or depressed",
        "I am slightly anxious or depressed",
        "I am moderately anxious or depressed",
        "I am severely anxious or depressed",
        "I am extremely anxious or depressed",
    ],
}

def get_timestamp():
    return datetime.datetime.now().isoformat()

DIGIT_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

async def collect_patient_id():
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid

async def run_eq5d5l_questionnaire():
    patient_id = await collect_patient_id()
    levels = []
    health_state_code = ""

    await robot_say("We will begin the EQ-5D-5L assessment. For each question, respond with 1 to 5.")

    for dimension, statements in eq5d5l_dimensions.items():
        await robot_say(f"{dimension} – please select one of the following:")
        for i, statement in enumerate(statements, 1):
            await robot_say(f"Option {i}: {statement}")

        while True:
            response = (await robot_listen()).lower()
            response = DIGIT_WORDS.get(response, response)
            if response.isdigit() and 1 <= int(response) <= 5:
                level = int(response)
                levels.append(level)
                health_state_code += str(level)
                await robot_say("Thank you.")
                send_to_server(
                    'responses_eq5d5l',
                    patient_id=patient_id,
                    timestamp=get_timestamp(),
                    dimension=dimension,
                    level=level,
                    health_state_code=None,
                    vas_score=None,
                )
                break
            else:
                await robot_say("Please answer with a number from one to five.")

    await robot_say("Now, rate your health today on a scale from 0 to 100.")
    while True:
        vas_input = (await robot_listen()).lower()
        vas_input = DIGIT_WORDS.get(vas_input, vas_input)
        if vas_input.isdigit() and 0 <= int(vas_input) <= 100:
            vas_score = int(vas_input)
            await robot_say("Thank you.")
            break
        else:
            await robot_say("Enter a number between zero and one hundred.")

    send_to_server(
        'responses_eq5d5l',
        patient_id=patient_id,
        timestamp=get_timestamp(),
        dimension='SUMMARY',
        level=None,
        health_state_code=health_state_code,
        vas_score=vas_score,
    )

    await robot_say(f"✅ EQ-5D-5L complete. Your health state code is: {health_state_code}")
    await robot_say(f"Your self-rated health (VAS) score is: {vas_score}")

    utility = calculate_placeholder_utility(levels)
    await robot_say(f"Estimated utility index (placeholder): {utility:.3f}")


def calculate_placeholder_utility(levels):
    decrement = sum((level - 1) * 0.1 for level in levels)
    utility = max(1.0 - decrement, 0.0)
    return utility

if __name__ == "__main__":
    asyncio.run(run_eq5d5l_questionnaire())
