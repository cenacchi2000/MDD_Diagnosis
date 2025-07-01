import asyncio
import uuid
import os
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

if not hasattr(system, "import_library"):
    raise RuntimeError("system.import_library missing")

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

speech_utils = system.import_library("./speech_utils.py")
robot_say = speech_utils.robot_say
robot_listen = speech_utils.robot_listen

remote_storage = system.import_library("./remote_storage.py")


# Interaction history utilities and robot state
INTERACTION_HISTORY = system.import_library(
    "../../../HB3/chat/knowledge/interaction_history.py"
)
ROBOT_STATE = system.import_library("../../../HB3/robot_state.py")
robot_state = ROBOT_STATE.state

speech_queue: asyncio.Queue[str] = asyncio.Queue()

async def listen() -> str:
    """Return the next recognized speech string from the queue or ASR."""
    if system.messaging is not None:
        return await speech_queue.get()
    return await robot_listen()

# Use the default LLM interface if available
try:
    llm = system.import_library("../../../HB3/lib/llm/llm_interface.py")
except Exception:
    llm = None

BeckDepression = system.import_library("./BeckDepression.py")
bpi_inventory = system.import_library("./bpi_inventory.py")
central_sensitization = system.import_library("./central_sensitization.py")
dass21_assessment = system.import_library("./dass21_assessment.py")
eq5d5l_assessment = system.import_library("./eq5d5l_assessment.py")
oswestry_disability_index = system.import_library("./oswestry_disability_index.py")
pain_catastrophizing = system.import_library("./pain_catastrophizing.py")
pittsburgh_sleep = system.import_library("./pittsburgh_sleep.py")

# Disable language model rephrasing unless explicitly requested
USE_LLM = os.environ.get("USE_LLM", "0") not in {"0", "false", "no"}

async def say_with_llm(text: str) -> None:
    """Speak text, optionally expanded through the LLM."""
    if USE_LLM and llm is not None:
        try:
            messages = [
                {"role": "system", "content": "You are Ameca, an empathetic healthcare assistant."},
                {"role": "user", "content": f"Please say the following to the patient: {text}"},
            ]
            resp = await llm.run_chat(model="gpt-4o", messages=messages)
            if resp and resp.get("content"):
                text = resp["content"]
        except Exception:
            pass
    await robot_say(text)


async def ask(question: str, key: str, store: dict, *, numeric: bool = False) -> str:
    """Ask a question and record the user's spoken answer."""
    await say_with_llm(question)

    ans = await listen()

    await robot_say("Thank you.")
    if numeric:
        ans = ans.lower()
        ans = {
            "zero": "0",
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
        }.get(ans, ans)
    store[key] = ans
    return ans

def store_demographics(pid: str, data: dict) -> None:
    remote_storage.send_to_server("patient_demographics", patient_id=pid, **data)

async def collect_demographics() -> str | None:
    await say_with_llm("Welcome to the Pain & Mood Assessment System")
    answers: dict[str, str] = {}

    last = await ask("Please tell me your last name", "name_last", answers)
    first = await ask("What is your first name?", "name_first", answers)

    patient_id = os.environ.get("patient_id", f"PAT-{uuid.uuid4().hex[:8]}")
    answers["patient_id"] = patient_id

    await say_with_llm(
        f"Hi {first}, nice to meet you. Today we will do a short interview to understand how you are feeling. Can I proceed with the assessment?"
    )

    proceed = (await listen()).lower()

    if proceed not in {"yes", "y"}:
        await robot_say("No problem, thank you for your answer I will ask my human colleague overstep.")
        return None

    await robot_say("Thank you, let's continue.")

    await ask("Middle initial if any", "name_middle", answers)
    await ask("Phone number", "phone", answers)
    await ask("Sex, M or F", "sex", answers)
    await ask("Date of birth in DD/MM/YYYY format", "dob", answers)
    await ask(
        "Marital Status: 1 for Single, 2 for Married, 3 for Widowed, 4 for Separated or Divorced",
        "marital_status",
        answers,
        numeric=True,
    )
    await ask(
        "Highest grade completed, enter 0 to 16 or M.A./M.S.",
        "education",
        answers,
        numeric=True,
    )
    await ask("Professional degree if any", "degree", answers)
    await ask("Current occupation", "occupation", answers)
    await ask("Spouse occupation if any", "spouse_occupation", answers)
    await ask(
        "Job status: 1 full time, 2 part time, 3 homemaker, 4 retired, 5 unemployed, 6 other",
        "job_status",
        answers,
        numeric=True,
    )
    await ask("How many months since diagnosis?", "diagnosis_time", answers, numeric=True)
    await ask("Pain due to present disease? 1 yes, 2 no, 3 uncertain", "disease_pain", answers, numeric=True)
    await ask("Was pain a symptom at diagnosis? 1 yes, 2 no, 3 uncertain", "pain_symptom", answers, numeric=True)
    surgery = await ask("Surgery in the past month? 1 yes, 2 no", "surgery", answers, numeric=True)
    if surgery == "1":
        await ask("What kind of surgery?", "surgery_type", answers)
    else:
        answers["surgery_type"] = ""
    await ask(
        "Experienced pain other than minor types last week? 1 yes, 2 no",
        "other_pain",
        answers,
        numeric=True,
    )
    await ask(
        "Taken pain medication in the last 7 days? 1 yes, 2 no",
        "pain_med_week",
        answers,
        numeric=True,
    )
    await ask(
        "Do you need daily pain medication? 1 yes, 2 no",
        "pain_med_daily",
        answers,
        numeric=True,
    )

    demog = dict(answers)
    demog["date"] = datetime.date.today().strftime("%d/%m/%Y")
    store_demographics(patient_id, demog)
    return patient_id

async def confirm(prompt: str) -> bool:
    """Ask the user whether to proceed with the given prompt."""
    await say_with_llm(prompt)
    ans = (await listen()).lower()
    return ans in {"yes", "y"}

async def run_all_assessments(pid: str) -> None:
    os.environ["patient_id"] = pid

    assessments = [
        ("Brief Pain Inventory", bpi_inventory.run_bpi),
        ("Central Sensitization Inventory", central_sensitization.run_csi_inventory),
        ("Central Sensitization worksheet", central_sensitization.run_csi_worksheet),
        ("DASS-21 questionnaire", dass21_assessment.run_dass21),
        ("EQ-5D-5L questionnaire", eq5d5l_assessment.run_eq5d5l_questionnaire),
        ("Oswestry Disability Index", oswestry_disability_index.run_odi),
        ("Pain Catastrophizing Scale", pain_catastrophizing.run_pcs),
        ("Pittsburgh Sleep Quality Index", pittsburgh_sleep.run_psqi),
        ("Beck Depression Inventory", BeckDepression.run_beck_depression_inventory),
    ]

    for name, func in assessments:
        if not await confirm(f"Would you like to begin the {name}? (Yes/No)"):
            await robot_say("Okay, stopping further assessments.")
            return
        await func()

async def main():
    pid = await collect_demographics()
    if not pid:
        return
    await run_all_assessments(pid)
    await robot_say("All assessments completed.")

class Activity:
    def on_start(self):
        robot_state = system.import_library("../../../HB3/robot_state.py").state
        self._task = robot_state.start_response_task(main())

    def on_stop(self):
        task = getattr(self, "_task", None)
        if task and not task.done():
            task.cancel()

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=10)
    def on_tick(self):
        task = getattr(self, "_task", None)
        if task and task.done():
            self.stop()


    async def on_message(self, channel, message):
        is_interaction = False
        if channel == "speech_recognized":
            system.messaging.post("processing_speech", True)
            speaker = message.get("speaker", None)
            event = INTERACTION_HISTORY.SpeechRecognisedEvent(
                message["text"], speaker=speaker, id=message.get("id", None)
            )
            for active_history in INTERACTION_HISTORY.InteractionHistory.get_registered(
                "TTS"
            ):
                active_history.add_to_memory(event)
            log.info(f"{speaker if speaker else 'User'}: {message['text']}")
            await speech_queue.put(message["text"])
            is_interaction = True

        if channel == "speech_recognized":
            system.messaging.post("processing_speech", False)


if __name__ == "__main__":
    asyncio.run(main())
