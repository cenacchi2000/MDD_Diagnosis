
import asyncio
import uuid
import os
import sys
import sqlite3

try:  # allow running inside or outside the robot system
    system  # type: ignore[name-defined]
except NameError:  # pragma: no cover - executed locally
    import builtins
    system = getattr(builtins, "system", None)

if system is None:
    import importlib.util

    class _LocalSystem:
        """Minimal stand-in for the robot system when running locally."""

        @staticmethod
        def import_library(rel_path: str):
            base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
            abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
            module_name = os.path.splitext(os.path.basename(rel_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, abs_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            return module

    system = _LocalSystem()
    import builtins
    builtins.system = system

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)

from remote_storage import send_to_server
from speech_utils import robot_say, robot_listen
import datetime

import BeckDepression
import bpi_inventory
import central_sensitization
import dass21_assessment
import eq5d5l_assessment
import oswestry_disability_index
import pain_catastrophizing
import pittsburgh_sleep

DB_PATH = os.path.join(MODULE_DIR, "patient_responses.db")

DIGIT_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
}

async def listen_clean() -> str:
    """Return normalized speech input with digits."""
    ans = await robot_listen()
    ans = ans.lower() if isinstance(ans, str) else ""
    return DIGIT_WORDS.get(ans, ans)


def timestamp() -> str:
    return datetime.datetime.now().isoformat()


async def ask(question: str, key: str, *, clean: bool = False, store: dict) -> str:
    """Prompt for an answer, store it and thank the user."""
    await robot_say(question)
    ans = await (listen_clean() if clean else robot_listen())
    await robot_say("Thank you.")
    store[key] = ans
    patient_id = store.get("patient_id")
    if patient_id:
        send_to_server(
            "patient_demographics",
            patient_id=patient_id,
            timestamp=timestamp(),
            field=key,
            value=ans,
        )
    return ans



def generate_patient_id():
    return f"PAT-{uuid.uuid4().hex[:8]}"

def lookup_patient_id(first_name: str, last_name: str) -> str | None:
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT patient_id FROM patient_demographics WHERE name_first=? AND name_last=?",
        (first_name, last_name),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

async def collect_demographics():
    await robot_say("Welcome to the Pain & Mood Assessment System")

    answers = {}

    name_last = await ask("Please tell me your last name", "name_last", store=answers)
    name_first = await ask("What is your first name?", "name_first", store=answers)

    env_id = os.environ.get("patient_id")
    existing = None
    if env_id:
        patient_id = env_id
    else:
        existing = lookup_patient_id(name_first, name_last)
        if existing:
            patient_id = existing
            await robot_say(f"Welcome back {name_first}. Proceeding to the assessment.")
            answers["patient_id"] = patient_id
            return patient_id
        patient_id = generate_patient_id()
    new_patient = env_id is None and existing is None
    answers["patient_id"] = patient_id

    date = datetime.date.today().strftime("%d/%m/%Y")

    await robot_say(
        f"Hi {name_first}, nice to meet you. Today we will do a short interview to understand how you are feeling. Can I proceed with the assessment?"
    )
    proceed = await listen_clean()
    if proceed not in {"yes", "y"}:
        await robot_say("No problem, thank you for your answer I will ask my human colleague overstep.")
        return None

    await robot_say("Thank you, let's continue.")

    name_middle = await ask("Middle initial if any", "name_middle", store=answers)
    phone = await ask("Phone number", "phone", store=answers)
    sex = await ask("Sex, M or F", "sex", store=answers)
    dob = await ask("Date of birth in DD/MM/YYYY format", "dob", store=answers)
    marital_status = await ask(
        "Marital Status: 1 for Single, 2 for Married, 3 for Widowed, 4 for Separated or Divorced",
        "marital_status",
        clean=True,
        store=answers,
    )
    education = await ask("Highest grade completed, enter 0 to 16 or M.A./M.S.", "education", clean=True, store=answers)
    degree = await ask("Professional degree if any", "degree", store=answers)
    occupation = await ask("Current occupation", "occupation", store=answers)
    spouse_occupation = await ask("Spouse occupation if any", "spouse_occupation", store=answers)
    job_status = await ask(
        "Job status: 1 full time, 2 part time, 3 homemaker, 4 retired, 5 unemployed, 6 other",
        "job_status",
        clean=True,
        store=answers,
    )
    diagnosis_time = await ask("How many months since diagnosis?", "diagnosis_time", clean=True, store=answers)
    disease_pain = await ask("Pain due to present disease? 1 yes, 2 no, 3 uncertain", "disease_pain", clean=True, store=answers)
    pain_symptom = await ask("Was pain a symptom at diagnosis? 1 yes, 2 no, 3 uncertain", "pain_symptom", clean=True, store=answers)
    surgery = await ask("Surgery in the past month? 1 yes, 2 no", "surgery", clean=True, store=answers)
    if surgery == "1":
        surgery_type = await ask("What kind of surgery?", "surgery_type", store=answers)
    else:
        surgery_type = ""
        send_to_server(
            "patient_demographics",
            patient_id=answers["patient_id"],
            timestamp=timestamp(),
            field="surgery_type",
            value=surgery_type,
        )
    other_pain = await ask("Experienced pain other than minor types last week? 1 yes, 2 no", "other_pain", clean=True, store=answers)
    pain_med_week = await ask("Taken pain medication in the last 7 days? 1 yes, 2 no", "pain_med_week", clean=True, store=answers)
    pain_med_daily = await ask("Do you need daily pain medication? 1 yes, 2 no", "pain_med_daily", clean=True, store=answers)

    if new_patient:
        demog = dict(answers)
        demog.pop("patient_id", None)
        demog["date"] = date
        store_demographics(patient_id, demog)

    return patient_id

def store_demographics(patient_id, data):
    send_to_server(
        'patient_demographics',
        patient_id=patient_id,
        **data,
    )

async def run_all_assessments(patient_id: str):
    """Run all questionnaires sequentially."""
    import os
    os.environ["patient_id"] = patient_id

    await bpi_inventory.run_bpi()
    await central_sensitization.run_csi_inventory()
    await central_sensitization.run_csi_worksheet()
    await dass21_assessment.run_dass21()
    await eq5d5l_assessment.run_eq5d5l_questionnaire()
    await oswestry_disability_index.run_odi()
    await pain_catastrophizing.run_pcs()
    await pittsburgh_sleep.run_psqi()
    await BeckDepression.run_beck_depression_inventory()

async def main():
    patient_id = await collect_demographics()
    if not patient_id:
        return
    await run_all_assessments(patient_id)
    await robot_say("All assessments completed.")


class Activity:
    async def on_start(self):
        await main()
        self.stop()


if __name__ == "__main__":
    asyncio.run(main())
