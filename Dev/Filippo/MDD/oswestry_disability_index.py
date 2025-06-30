
import os
import uuid
import datetime

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



# Generate patient ID or accept user-defined one
def get_patient_id() -> str:
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid

def get_timestamp():
    return datetime.datetime.now().isoformat()

DIGIT_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
}



# Questionnaire structure
questions = [
    ("Which statement best describes your current pain intensity?", [
        "I can tolerate the pain I have without having to use pain killers",
        "The pain is bad but I manage without taking pain killers",
        "Pain killers give complete relief from pain",
        "Pain killers give moderate relief from pain",
        "Pain killers give very little relief from pain",
        "Pain killers have no effect on the pain and I do not use them"
    ]),
    ("Which option best reflects how pain affects your personal care?", [
        "I can look after myself normally without causing extra pain",
        "I can look after myself normally but it causes extra pain",
        "It is painful to look after myself and I am slow and careful",
        "I need some help but manage most of my personal care",
        "I need help every day in most aspects of self care",
        "I don’t get dressed, I wash with difficulty and stay in bed"
    ]),
    ("Which statement best reflects your ability to lift items?", [
        "I can lift heavy weights without extra pain",
        "I can lift heavy weights but it gives extra pain",
        "Pain prevents me from lifting heavy weights off the floor, but I can manage if they are on a table",
        "Pain prevents me from lifting heavy weights, but I can manage light to medium weights",
        "I can lift very light weights",
        "I cannot lift or carry anything at all"
    ]),
    ("Which statement best describes your walking ability?", [
        "Pain does not prevent me walking any distance",
        "Pain prevents me walking more than one mile",
        "Pain prevents me walking more than ½ mile",
        "Pain prevents me walking more than ¼ mile",
        "I can only walk using a stick or crutches",
        "I am in bed most of the time and have to crawl to the toilet"
    ]),
    ("Which statement best describes your ability to sit?", [
        "I can sit in any chair as long as I like",
        "I can only sit in my favorite chair as long as I like",
        "Pain prevents me from sitting more than one hour",
        "Pain prevents me from sitting more than ½ hour",
        "Pain prevents me from sitting more than 10 minutes",
        "Pain prevents me from sitting at all"
    ]),
    ("Which statement best describes how long you can stand?", [
        "I can stand as long as I want without extra pain",
        "I can stand as long as I want but it gives me extra pain",
        "Pain prevents me from standing for more than one hour",
        "Pain prevents me from standing for more than 30 minutes",
        "Pain prevents me from standing for more than 10 minutes",
        "Pain prevents me from standing at all"
    ]),
    ("Which statement best describes how pain affects your sleep?", [
        "Pain does not prevent me from sleeping well",
        "I can sleep well only by using medication",
        "Even when I take medication, I have less than 6 hrs sleep",
        "Even when I take medication, I have less than 4 hrs sleep",
        "Even when I take medication, I have less than 2 hrs sleep",
        "Pain prevents me from sleeping at all"
    ]),
    ("Which statement best describes how pain affects your social life?", [
        "My social life is normal and gives me no extra pain",
        "My social life is normal but increases the degree of pain",
        "Pain has no significant effect apart from limiting energetic interests",
        "Pain has restricted my social life and I don’t go out as often",
        "Pain has restricted my social life to my home",
        "I have no social life because of pain"
    ]),
    ("Which statement best describes how pain affects your travel?", [
        "I can travel anywhere without extra pain",
        "I can travel anywhere but it gives me extra pain",
        "Pain is bad, but I manage journeys over 2 hours",
        "Pain restricts me to journeys of less than 1 hour",
        "Pain restricts me to short necessary journeys under 30 minutes",
        "Pain prevents me from traveling except to the doctor or hospital"
    ]),
    ("Which statement best describes how pain affects your work or homemaking?", [
        "My normal job activities do not cause pain",
        "My normal job activities increase pain, but I can still perform all duties",
        "I can perform most duties, but pain prevents me from strenuous tasks",
        "Pain prevents me from doing anything but light duties",
        "Pain prevents me from doing even light duties",
        "Pain prevents me from performing any job or chores"
    ])
]

def interpret_score(total_score):
    if total_score <= 4:
        return "No disability"
    elif total_score <= 14:
        return "Mild disability"
    elif total_score <= 24:
        return "Moderate disability"
    elif total_score <= 34:
        return "Severe disability"
    else:

        return "Completely disabled"

async def run_odi():
    patient_id = get_patient_id()
    total_score = 0
    for i, (title, options) in enumerate(questions, start=1):
        await robot_say(f"Q{i}. {title}")
        for idx, opt in enumerate(options):
            await robot_say(f"Option {idx}: {opt}")

        while True:
            user_input = (await robot_listen()).lower()
            user_input = DIGIT_WORDS.get(user_input, user_input)
            if user_input.isdigit() and 0 <= int(user_input) < len(options):
                score = int(user_input)
                await robot_say("Thank you.")
                break
            await robot_say("Invalid input. Choose a number from zero to five.")

        total_score += score
        send_to_server(
            'responses_odi',
            patient_id=patient_id,
            timestamp=get_timestamp(),
            question_number=i,
            question_text=title,
            selected_option=options[score],
            score=score,
        )

    await robot_say(f"ODI Complete. Total Score: {total_score} / 50")
    level = interpret_score(total_score)
    await robot_say(f"Disability Level: {level}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_odi())

