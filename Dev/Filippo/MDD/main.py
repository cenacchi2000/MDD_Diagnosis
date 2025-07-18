import asyncio
import uuid
import os
import datetime
import re
from typing import Any

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
UTILS = system.import_library("../../../HB3/utils.py")
SCRIPTS = [
    "../../../HB3/Perception/Add_Speech.py",
    "../../../HB3/Human_Animation/Anim_Talking_Sequence.py",
]


# Interaction history utilities and robot state
INTERACTION_HISTORY = system.import_library(
    "../../../HB3/chat/knowledge/interaction_history.py"
)
ROBOT_STATE = system.import_library("../../../HB3/robot_state.py")
robot_state = ROBOT_STATE.state

speech_queue: asyncio.Queue[str] = asyncio.Queue()
# Future used by ask() to wait for the next recognised utterance
answer_future: asyncio.Future[str] | None = None


async def _run_pactl(*args: str):
    process = await asyncio.create_subprocess_exec(
        "pactl",
        *args,
        env={"PULSE_RUNTIME_PATH": "/tmp/pulseaudio"},
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    await process.wait()
    return process


async def _get_volume() -> int:
    try:
        proc = await _run_pactl("get-sink-volume", "@DEFAULT_SINK@")
        out = (await proc.stdout.read(4096)).decode()
        m = re.search(r"front-left: (\d+) /", out)
        if m:
            return round(int(m.group(1)) / 65536 * 100)
    except Exception:
        pass
    return 0


async def _set_volume(level: int) -> None:
    try:
        await _run_pactl(
            "set-sink-volume",
            "@DEFAULT_SINK@",
            str(level * 65536 // 100),
        )
    except Exception:
        pass


async def ensure_volume(min_level: int = 50) -> None:
    current = await _get_volume()
    if current and current < min_level:
        await _set_volume(min_level)



async def _send_history_async(**data: Any) -> None:
    """Send recognised speech to the backend without blocking."""

    try:
        await asyncio.to_thread(remote_storage.send_to_server, "conversation_history", **data)
    except Exception:
        pass



def _patch_llm_decider_mode() -> None:
    """Prevent unscripted LLM replies during assessments."""

    try:
        llm_mod = system.import_library(
            "../../../HB3/chat/modes/llm_decider_mode.py"
        )
    except Exception:
        return

    if getattr(llm_mod, "_mdd_patch_applied", False):
        return

    original_on_message = llm_mod.LLMDeciderMode.on_message

    async def patched_on_message(self, channel: str, message: Any):
        if channel == "speech_recognized" and os.environ.get("MDD_ASSESSMENT_ACTIVE"):
            return
        return await original_on_message(self, channel, message)

    llm_mod.LLMDeciderMode.on_message = patched_on_message
    llm_mod._mdd_patch_applied = True


async def listen(timeout: float | None = None) -> str:
    """Return the next recognized speech string from the queue or ASR."""

    if system.messaging is not None:
        if timeout is None:
            return await speech_queue.get()
        try:
            return await asyncio.wait_for(speech_queue.get(), timeout)
        except asyncio.TimeoutError:
            return ""
    return await robot_listen()


async def wait_for_answer() -> str:
    """Return the next recognised speech and clear the waiting future."""
    global answer_future
    loop = asyncio.get_running_loop()
    answer_future = loop.create_future()
    try:
        return await answer_future
    finally:
        answer_future = None


BeckDepression = system.import_library("./BeckDepression.py")
bpi_inventory = system.import_library("./bpi_inventory.py")
central_sensitization = system.import_library("./central_sensitization.py")
dass21_assessment = system.import_library("./dass21_assessment.py")
eq5d5l_assessment = system.import_library("./eq5d5l_assessment.py")
oswestry_disability_index = system.import_library("./oswestry_disability_index.py")
pain_catastrophizing = system.import_library("./pain_catastrophizing.py")
pittsburgh_sleep = system.import_library("./pittsburgh_sleep.py")



# Previous chat mode so we can restore it after assessments
PREVIOUS_MODE: str | None = None


async def say_with_llm(text: str) -> None:
    """Speak text directly without using the language model."""
    await robot_say(text)


async def ask(question: str, key: str, store: dict, *, numeric: bool = False) -> str:
    """Ask a question and record the user's spoken answer."""

    await robot_say(question)

    # Clear any leftover utterances from the previous answer
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
        except asyncio.QueueEmpty:
            break



    ans = ""
    while not ans:
        ans = (await wait_for_answer()).strip()
        if not ans:
            await robot_say("I didn't catch that, please repeat.")


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

    """Store demographics for ``pid`` ensuring the ID is included once."""
    payload = dict(data)
    payload["patient_id"] = pid
    remote_storage.send_to_server("patient_demographics", **payload)


async def collect_demographics() -> str | None:
    answers: dict[str, str] = {}


    last = await ask(
        "Welcome to the Pain & Mood Assessment System, today I will ask you a few questions to understand how you are feeling. Lets start, what is your last name?",
        "name_last",
        answers,
    )

    first = await ask(
        "Thank you very much for your answer, and what is your first name?",
        "name_first",
        answers,
    )

    patient_id = os.environ.get("patient_id", f"PAT-{uuid.uuid4().hex[:8]}")
    answers["patient_id"] = patient_id

    await ask(
        "Thank you for your answer, what is the reason for your visit to the clinic today?",
        "reason_visit",
        answers,
    )
    await ask("Thank you for your answer, then before we start let me ask you some demographic questions. Lets start with in which country were you born?", "country_of_origin", answers)
    await ask("Thank you for your answer, what is your gender?                          Please feel free to answer that you wish to not specify", "gender", answers)
    await ask(
        "Thank you for your answer, what is your date of birth?",
        "dob",
        answers,
    )
    await ask(
        "Thank you for your answer, what is your marital status? Please answer one of the following: Single, In a Relationship, Married, Widowed, Separated or Divorced",
        "marital_status",
        answers,
        numeric=True,
    )
    await ask(
        "Thank you for your very much for your answers just a few more questions. What is the highest grade of education you have completed?",
        "education",
        answers,
        numeric=True,
    )

    await ask("Thank you and what is your current occupation?", "occupation", answers)

    await ask(

        "Thank you for your answer, what is your job status: Full time, Part time, Retired, Unemployed or Other",
        "job_status",
        answers,
        numeric=True,
    )
    await ask(
        "Ok! Thank you very much for all of your answers, Lets dive in into the clinical assessment. I will start with a few questions about your pain conditions. When were you first diagnosed with pain",
        "diagnosis_time",
        answers,
        numeric=True,
    )
    await ask(
        "I the current pain due to a present disease that you have?",
        "disease_pain",
        answers,
        numeric=True,
    )
    await ask(
        "Was pain a symptom at diagnosis?",
        "pain_symptom",
        answers,
        numeric=True,
    )
    surgery = await ask(
        "Did you have a surgery in the past month? please answer yes or no",
        "surgery",
        answers,
        numeric=True,
    )
    if surgery == "Yes":
        await ask("Thank you for your answer, what kind of surgery did you do?", "surgery_type", answers)
    else:
        answers["surgery_type"] = ""
    await ask(
        "Thank you for your answer, Did you experience any pain other than minor episodes last week?",
        "other_pain",
        answers,
        numeric=True,
    )
    await ask(
        "Ok, and have you taken any pain medication in the last 7 days?",
        "pain_med_week",
        answers,
        numeric=True,
    )
    await ask(
        "Perfect and last question, do you need or are prescribed any daily pain medication?",
        "pain_med_daily",
        answers,
        numeric=True,
    )

    await say_with_llm("Ok all done with the intial questions, You did great! I got all the data I needed to remember you next time, thank you for your time and for your collaboration so far.")

    demog = dict(answers)
    demog["date"] = datetime.date.today().strftime("%d/%m/%Y")
    store_demographics(patient_id, demog)

    await robot_say(
        f"So {first}, in order for me to assess your case I will ask you some questions that will allow me to locate and evaluate the pain and possible comorbid symptoms. Please let me know if I can proceed with the assessment?"
    )

    proceed = (await listen()).lower()

    if proceed not in {"yes", "y"}:
        await say_with_llm(
            "No problem, thank you for your answers and for your time so far, I will now ask my human colleague to overstep."
        )
        return None

    await say_with_llm("Let's continue then.")
    return patient_id

async def confirm(prompt: str) -> bool:
    """Ask the user whether to proceed with the given prompt."""
    await robot_say(prompt)
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
        if not await confirm(f"Perfect, I have completed the {name} assessment. Can I continue with the next assessment?"):
            await say_with_llm("Okay, stopping further assessments.")
            return
        await func()

async def _run_assessment() -> None:
    """Run the demographic questions and all questionnaires."""
    pid = await collect_demographics()
    if not pid:
        return
    await run_all_assessments(pid)
    await say_with_llm("All assessments completed.")


async def main() -> None:
    """Entry point for the assessment.

    Applies the LLM patch and sets the required environment variable so the
    language model does not respond with unscripted text when running the
    assessment directly from the command line.
    """
    _patch_llm_decider_mode()
    if "patient_id" not in os.environ:
        os.environ["patient_id"] = f"PAT-{uuid.uuid4().hex[:8]}"
    os.environ["MDD_ASSESSMENT_ACTIVE"] = "1"
    await ensure_volume(50)

    try:
        await _run_assessment()
    finally:
        os.environ.pop("MDD_ASSESSMENT_ACTIVE", None)

class Activity:
    def on_start(self):
        robot_state = system.import_library("../../../HB3/robot_state.py").state
        mode_ctrl = system.import_library("../../../HB3/chat/mode_controller.py")

        global PREVIOUS_MODE
        PREVIOUS_MODE = mode_ctrl.ModeController.get_current_mode_name() or "interaction"


        _patch_llm_decider_mode()

        os.environ["MDD_ASSESSMENT_ACTIVE"] = "1"

        self._scripts = []
        for script in SCRIPTS:
            self._scripts.append(UTILS.start_other_script(system, script))

        self._task = robot_state.start_response_task(main())

    def on_stop(self):
        task = getattr(self, "_task", None)
        if task and not task.done():
            task.cancel()
        # Restore normal interaction mode

        for script in getattr(self, "_scripts", []):
            UTILS.stop_other_script(system, script)

        if PREVIOUS_MODE is not None and system.messaging is not None:
            system.messaging.post("mode_change", PREVIOUS_MODE)

        os.environ.pop("MDD_ASSESSMENT_ACTIVE", None)


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

            asyncio.create_task(
                _send_history_async(

                    timestamp=datetime.datetime.now().isoformat(),
                    speaker=speaker or "user",
                    text=message["text"],
                    id=message.get("id") or "",
                )

            )

            await speech_queue.put(message["text"])
            if answer_future is not None and not answer_future.done():
                answer_future.set_result(message["text"])
            is_interaction = True

        if channel == "speech_recognized":
            system.messaging.post("processing_speech", False)


if __name__ == "__main__":
    asyncio.run(main())
