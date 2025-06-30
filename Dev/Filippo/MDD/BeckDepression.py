# Beck Depression Inventory (BDI) - Integrated with shared database (patient_responses.db)


import datetime
import asyncio
import uuid
import os

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

        @staticmethod
        def tick(*, fps: int = 10):
            """Return a decorator that simply returns the function."""
            def decorator(func):
                return func
            return decorator

    system = _LocalSystem()
    builtins.system = system

send_to_server = system.import_library("./remote_storage.py").send_to_server
speech_mod = system.import_library("./speech_utils.py")
robot_say = speech_mod.robot_say
robot_listen = speech_mod.robot_listen

# Generate patient ID, preferring environment variable
def get_patient_id() -> str:
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid

# map spoken numbers to digits
DIGIT_WORDS = {"zero": "0", "one": "1", "two": "2", "three": "3"}


async def store_response_to_db(patient_id: str, question_number: int, question_title: str, answer: str, score: int):
    """Send response data to the remote server."""
    timestamp = datetime.datetime.now().isoformat()
    send_to_server(
        'responses_bdi',
        patient_id=patient_id,
        timestamp=timestamp,
        question_number=question_number,
        question_title=question_title,
        answer=answer,
        score=score,
    )


bdi_questions = [
    ("How sad have you been feeling?", ["I do not feel sad.", "I feel sad.", "I am sad all the time and can't snap out of it.", "I am so sad and unhappy that I can't stand it."]),
    ("How pessimistic do you feel about the future?", ["I am not particularly discouraged about the future.", "I feel discouraged about the future.", "I feel I have nothing to look forward to.", "I feel the future is hopeless and that things cannot be done."]),
    ("Do you feel like a failure?", ["I do not feel like a failure.", "I feel I have failed more than the average person.", "As I look back on my life, all I can see is a lot of failures.", "I feel I am a complete failure as a person."]),
    ("How satisfied do you feel with your life?", ["I get as much satisfaction out of things as I used to.", "I don’t enjoy things the way I used to.", "I don't get real satisfaction out of anything anymore.", "I am dissatisfied or bored with everything."]),
    ("How often do you feel guilty?", ["I don’t feel particularly guilty.", "I feel guilty a good part of the time.", "I feel quite guilty most of the time.", "I feel guilty all of the time."]),
    ("Do you feel you are being punished?", ["I don’t feel I am being punished.", "I feel I may be punished.", "I expect to be punished.", "I feel I am being punished."]),
    ("How disappointed are you in yourself?", ["I don’t feel disappointed in myself.", "I am disappointed in myself.", "I am disgusted with myself.", "I hate myself."]),
    ("How critical are you of yourself?", ["I don’t feel I am any worse than anybody else.", "I am critical of myself for my weakness or mistakes.", "I blame myself all the time for my faults.", "I blame myself for everything bad that happens."]),
    ("Have you had thoughts of killing yourself?", ["I don’t have any thoughts of killing myself.", "I have thoughts of killing myself, but I would not carry them out.", "I would like to kill myself.", "I would kill myself if I had the chance."]),
    ("How often do you feel like crying?", ["I don’t cry any more than usual.", "I cry more now than I used to.", "I cry all the time now.", "I used to be able to cry, but now I can’t cry even though I want to."]),
    ("How irritable do you feel?", ["I am no more irritated by things than I ever was.", "I am slightly more irritated now than usual.", "I am quite annoyed or irritated a good deal of the time.", "I feel irritated all the time."]),
    ("How much have you lost interest in other people?", ["I have not lost interest in other people.", "I am less interested in other people than I used to be.", "I have lost most of my interest in other people.", "I have lost all of my interest in other people."]),
    ("How difficult is it for you to make decisions?", ["I make decisions about as well as I ever could.", "I put off making decisions more than I used to.", "I have greater difficulty in making decisions more than I used to.", "I can't make decisions at all anymore."]),
    ("How do you feel about your appearance?", ["I don’t feel that I look any worse than I used to.", "I am worried that I am looking old or unattractive.", "I feel there are permanent changes in my appearance that make me look unattractive.", "I believe that I look ugly."]),
    ("How capable do you feel of working?", ["I can work about as well as before.", "It takes an extra effort to get started at doing something.", "I have to push myself very hard to do anything.", "I can't do any work at all."]),
    ("How well are you sleeping?", ["I can sleep as well as usual.", "I don’t sleep as well as I used to.", "I wake up 1–2 hours earlier than usual and find it hard to get back to sleep.", "I wake up several hours earlier than I used to and cannot get back to sleep."]),
    ("How tired do you feel?", ["I don't get more tired than usual.", "I get tired more easily than I used to.", "I get tired from doing almost anything.", "I am too tired to do anything."]),
    ("How is your appetite?", ["My appetite is no worse than usual.", "My appetite is not as good as it used to be.", "My appetite is much worse now.", "I have no appetite at all anymore."]),
    ("Have you experienced weight loss recently?", ["I haven't lost much weight, if any, lately.", "I have lost more than five pounds.", "I have lost more than ten pounds.", "I have lost more than fifteen pounds."]),
    ("How worried are you about your health?", ["I am no more worried about my health than usual.", "I am worried about physical problems like aches, pain, upset stomach or constipation.", "I am very worried about physical problems and it's hard to think of much else.", "I am so worried about my physical problems that I cannot think of anything else."]),
    ("How is your interest in sex?", ["I have not noticed any recent changes in my interest in sex.", "I am less interested in sex than I used to be.", "I have almost no interest in sex.", "I have lost interest in sex completely."])
]


async def run_beck_depression_inventory():
    patient_id = get_patient_id()
    total_score = 0
    for i, (title, options) in enumerate(bdi_questions):
        await robot_say(f"Question {i+1} - {title}:")
        for idx, opt in enumerate(options):
            await robot_say(f"Option {idx}: {opt}")

        valid = False
        while not valid:
            response = (await robot_listen()).lower()
            response = DIGIT_WORDS.get(response, response)
            if response in {"0", "1", "2", "3"}:
                score = int(response)
                valid = True
                await robot_say("Thank you.")
            else:
                await robot_say("Please answer with zero, one, two, or three.")


        total_score += score
        await store_response_to_db(patient_id, i+1, title, options[score], score)

    await robot_say(f"You have completed the questionnaire. Your total score is {total_score}.")
    category = interpret_score(total_score)
    await robot_say(f"According to the Beck Depression Inventory, this corresponds to: {category}")
    return f"Total score: {total_score} – {category}"

def interpret_score(score: int) -> str:
    if score <= 10:
        return "These ups and downs are considered normal."
    elif score <= 16:
        return "Mild mood disturbances."
    elif score <= 20:
        return "Borderline clinical depression."
    elif score <= 30:
        return "Moderate depression."
    elif score <= 40:
        return "Severe depression."
    else:
        return "Extreme depression."

if __name__ == "__main__":
    asyncio.run(run_beck_depression_inventory())
