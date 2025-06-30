# Pittsburgh Sleep Quality Index (PSQI) implementation script

import asyncio
import datetime
import os
import uuid
from typing import Literal

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





def get_timestamp():
    return datetime.datetime.now().isoformat()


def get_patient_id():
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid


# Map responses to scores as per PSQI guidance
frequency_score = {
    "not during the past month": 0,
    "less than once a week": 1,
    "once or twice a week": 2,
    "three or more times a week": 3
}

problem_score = {
    "no problem at all": 0,
    "only a very slight problem": 1,
    "somewhat of a problem": 2,
    "a very big problem": 3
}

rating_score = {
    "very good": 0,
    "fairly good": 1,
    "fairly bad": 2,
    "very bad": 3
}

async def ask_and_store(patient_id, qnum, text, score_map=None):
    """Ask a question, store the response and return the raw answer with its score."""
    await robot_say(text)
    ans = (await robot_listen()).lower()
    score = score_map[ans] if score_map and ans in score_map else -1
    await robot_say("Thank you.")
    send_to_server(
        'responses_psqi',
        patient_id=patient_id,
        timestamp=get_timestamp(),
        question_number=qnum,
        question_text=text,
        answer=ans.title(),
        score=score,
    )
    return ans, score

def _parse_time_to_hours(timestr: str) -> float:
    """Convert HH:MM formatted string to decimal hours."""
    try:
        t = datetime.datetime.strptime(timestr, "%H:%M").time()
    except ValueError:
        raise ValueError(f"Time '{timestr}' not in HH:MM format")
    return t.hour + t.minute / 60

async def run_psqi():
    patient_id = get_patient_id()
    await robot_say("Starting Pittsburgh Sleep Quality Index (PSQI)")

    # Part 1: Raw numeric entries
    await robot_say("Enter time values in 24h format (e.g., 23:30) or hours as numbers.")
    bedtime_str, _ = await ask_and_store(patient_id, "1", "What time have you usually gone to bed at night?")
    latency = int(await robot_listen())  # minutes to fall asleep
    send_to_server(
        'responses_psqi',
        patient_id=patient_id,
        timestamp=get_timestamp(),
        question_number="2",
        question_text="How long to fall asleep in minutes:",
        answer=str(latency),
        score=-1,
    )
    waketime_str, _ = await ask_and_store(patient_id, "3", "What time have you usually gotten up in the morning?")
    sleep_hours = float(await robot_listen())
    send_to_server(
        'responses_psqi',
        patient_id=patient_id,
        timestamp=get_timestamp(),
        question_number="4",
        question_text="How many hours of actual sleep per night:",
        answer=str(sleep_hours),
        score=-1,
    )

    # Part 2: Disturbance checklist (5a–j)
    disturbance_sum = 0
    for i, disturbance in enumerate([
        "5a. Cannot get to sleep within 30 minutes",
        "5b. Wake up in the middle of the night or early morning",
        "5c. Have to get up to use the bathroom",
        "5d. Cannot breathe comfortably",
        "5e. Cough or snore loudly",
        "5f. Feel too cold",
        "5g. Feel too hot",
        "5h. Have bad dreams",
        "5i. Have pain",
        "5j. Other reason(s), describe"
    ], start=5):
        _, score = await ask_and_store(patient_id, str(i), disturbance, frequency_score)
        if score != -1:
            disturbance_sum += score

    # Questions 6–9
    _, med_use = await ask_and_store(patient_id, "6", "How often have you taken medicine to help you sleep?", frequency_score)
    _, trouble_awake = await ask_and_store(patient_id, "7", "Trouble staying awake (e.g., driving, eating, social)?", frequency_score)
    _, enthusiasm = await ask_and_store(patient_id, "8", "How much of a problem has lack of enthusiasm been?", problem_score)
    _, subjective_quality = await ask_and_store(patient_id, "9", "Rate your sleep quality overall:", rating_score)

    # Component scoring based on rules
    comp1 = subjective_quality
    comp2_score = 0
    if latency <= 15: latency_score = 0
    elif latency <= 30: latency_score = 1
    elif latency <= 60: latency_score = 2
    else: latency_score = 3

    _, latency_freq = await ask_and_store(patient_id, "5a (recheck)", "Frequency of taking more than 30 min to fall asleep:", frequency_score)
    comp2_sum = latency_score + latency_freq
    if comp2_sum == 0: comp2_score = 0
    elif comp2_sum <= 2: comp2_score = 1
    elif comp2_sum <= 4: comp2_score = 2
    else: comp2_score = 3

    comp3_score = 0 if sleep_hours > 7 else 1 if sleep_hours > 6 else 2 if sleep_hours > 5 else 3

    # Bed and wake time for sleep efficiency
    bed_hour = _parse_time_to_hours(bedtime_str)
    wake_hour = _parse_time_to_hours(waketime_str)
    time_in_bed = (wake_hour - bed_hour + 24) % 24
    efficiency = (sleep_hours / time_in_bed) * 100 if time_in_bed > 0 else 0
    if efficiency > 85: comp4_score = 0
    elif efficiency >= 75: comp4_score = 1
    elif efficiency >= 65: comp4_score = 2
    else: comp4_score = 3

    if disturbance_sum == 0: comp5_score = 0
    elif disturbance_sum <= 9: comp5_score = 1
    elif disturbance_sum <= 18: comp5_score = 2
    else: comp5_score = 3

    comp6_score = med_use

    daytime_sum = trouble_awake + enthusiasm
    if daytime_sum == 0: comp7_score = 0
    elif daytime_sum <= 2: comp7_score = 1
    elif daytime_sum <= 4: comp7_score = 2
    else: comp7_score = 3

    global_score = sum([comp1, comp2_score, comp3_score, comp4_score, comp5_score, comp6_score, comp7_score])

    await robot_say(f"Your global PSQI score is: {global_score} (0–21). Higher scores = worse sleep quality.")

if __name__ == "__main__":
    asyncio.run(run_psqi())
