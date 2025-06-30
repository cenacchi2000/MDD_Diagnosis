# Script to administer the full Brief Pain Inventory (BPI), auto-generate patient ID, and store structured answers
# in SQLite (patient_responses.db)


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


def get_patient_id() -> str:
    """Retrieve patient ID from environment or auto-generate."""
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid





# Long-form BPI Questions — simplified text w/ freeform or numeric entry
bpi_questions = [
    "1. Rate your pain at its worst in the last 24 hours (0 = No pain, 10 = Worst imaginable):",
    "2. Rate your pain at its least in the last 24 hours (0 = No pain, 10 = Worst imaginable):",
    "3. Rate your average pain (0 = No pain, 10 = Worst imaginable):",
    "4. Rate your pain right now (0 = No pain, 10 = Worst imaginable):",
    "5a. Do you have pain in more than one location? (Yes/No):",
    "5b. Mark the areas where you feel pain (free description):",
    "6. When did your pain start? (e.g., '1 month ago', '3 days ago'):",
    "7. What causes or increases your pain? (free response):",
    "8. What relieves your pain? (free response):",
    "9a. In the last 24 hours, how much relief have pain treatments given you? (0%–100%):",
    "10a. Pain interfered with General Activity (0 = No interference, 10 = Complete interference):",
    "10b. How has your mood been affected by pain?",
    "10c. How has pain affected your walking ability?",
    "10d. How has pain interfered with your normal work?",
    "10e. How has pain affected your relations with others?",
    "10f. How has pain affected your sleep?",
    "10g. How has pain affected your enjoyment of life?",
    "11. Are you currently taking pain medications? (Yes/No):",
    "12a. If yes, list your current medications:",
    "12b. How often do you take these medications?:",
    "12c. How well are these medications working?:",
    "13. Have you had any side effects from your pain medications? (Yes/No):",
    "14. List any side effects experienced:",
    "15. Any other comments about your pain or treatment?"
]

# Auto-adjust question numbering (we split compound questions)

async def run_bpi():
    patient_id = get_patient_id()

    index = 0
    qnum = 1
    while index < len(bpi_questions):
        question = bpi_questions[index]
        await robot_say(question)
        response = await robot_listen()
        await robot_say("Thank you.")
        timestamp = datetime.datetime.now().isoformat()

        send_to_server(
            'responses_bpi',
            patient_id=patient_id,
            timestamp=timestamp,
            question_number=qnum,
            question_text=question,
            response=response,
        )
        qnum += 1

        resp_lower = response.strip().lower()

        # Conditional follow-ups
        if index == 4 and resp_lower not in {"yes", "y"}:
            index += 2  # skip 5b
            continue
        if index == 17 and resp_lower not in {"yes", "y"}:
            index += 4  # skip 12a-c
            continue
        if index == 21 and resp_lower not in {"yes", "y"}:
            index += 2  # skip question 14
            continue

        index += 1

    await robot_say(f"All responses saved for Patient ID: {patient_id}")


if __name__ == "__main__":
    asyncio.run(run_bpi())
