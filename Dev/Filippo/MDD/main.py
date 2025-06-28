
import asyncio
import uuid
import os
import sys
import sqlite3

sys.path.append(os.path.dirname(__file__))
from remote_storage import send_to_server
ROBOT_STATE = system.import_library("../../../HB3/robot_state.py")
robot_state = ROBOT_STATE.state

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

DB_PATH = os.path.join(os.path.dirname(__file__), "patient_responses.db")

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
    ans = (await robot_listen()).lower()
    return DIGIT_WORDS.get(ans, ans)




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

    await robot_say("Please tell me your last name")
    name_last = await robot_listen()

    await robot_say("What is your first name?")
    name_first = await robot_listen()

    env_id = os.environ.get("patient_id")
    existing = None
    if env_id:
        patient_id = env_id
    else:
        existing = lookup_patient_id(name_first, name_last)
        if existing:
            patient_id = existing
            await robot_say(f"Welcome back {name_first}. Proceeding to the assessment.")
            return patient_id
        patient_id = generate_patient_id()
    new_patient = env_id is None and existing is None

    date = datetime.date.today().strftime("%d/%m/%Y")

    await robot_say(
        f"Hi {name_first}, nice to meet you. Today we will do a short interview to understand how you are feeling. Can I proceed with the assessment?"
    )
    proceed = await listen_clean()
    if proceed not in {"yes", "y"}:
        await robot_say("No problem, thank you for your answer I will ask my human colleague overstep.")
        return None

    await robot_say("Thank you, let's continue.")

    await robot_say("Middle initial if any")
    name_middle = await robot_listen()

    await robot_say("Phone number")
    phone = await robot_listen()

    await robot_say("Sex, M or F")
    sex = await robot_listen()

    await robot_say("Date of birth in DD/MM/YYYY format")
    dob = await robot_listen()

    await robot_say("Marital Status: 1 for Single, 2 for Married, 3 for Widowed, 4 for Separated or Divorced")
    marital_status = await listen_clean()

    await robot_say("Highest grade completed, enter 0 to 16 or M.A./M.S.")
    education = await listen_clean()

    await robot_say("Professional degree if any")
    degree = await robot_listen()

    await robot_say("Current occupation")
    occupation = await robot_listen()

    await robot_say("Spouse occupation if any")
    spouse_occupation = await robot_listen()

    await robot_say("Job status: 1 full time, 2 part time, 3 homemaker, 4 retired, 5 unemployed, 6 other")
    job_status = await listen_clean()

    await robot_say("How many months since diagnosis?")
    diagnosis_time = await listen_clean()

    await robot_say("Pain due to present disease? 1 yes, 2 no, 3 uncertain")
    disease_pain = await listen_clean()

    await robot_say("Was pain a symptom at diagnosis? 1 yes, 2 no, 3 uncertain")
    pain_symptom = await listen_clean()

    await robot_say("Surgery in the past month? 1 yes, 2 no")
    surgery = await listen_clean()

    if surgery == "1":
        await robot_say("What kind of surgery?")
        surgery_type = await robot_listen()
    else:
        surgery_type = ""

    await robot_say("Experienced pain other than minor types last week? 1 yes, 2 no")
    other_pain = await listen_clean()

    await robot_say("Taken pain medication in the last 7 days? 1 yes, 2 no")
    pain_med_week = await listen_clean()

    await robot_say("Do you need daily pain medication? 1 yes, 2 no")
    pain_med_daily = await listen_clean()

    if new_patient:
        store_demographics(
            patient_id,
            {
                "date": date,
                "name_last": name_last,
                "name_first": name_first,
                "name_middle": name_middle,
                "phone": phone,
                "sex": sex,
                "dob": dob,
                "marital_status": marital_status,
                "education": education,
                "degree": degree,
                "occupation": occupation,
                "spouse_occupation": spouse_occupation,
                "job_status": job_status,
                "diagnosis_time": diagnosis_time,
                "disease_pain": disease_pain,
                "pain_symptom": pain_symptom,
                "surgery": surgery,
                "surgery_type": surgery_type,
                "other_pain": other_pain,
                "pain_med_week": pain_med_week,
                "pain_med_daily": pain_med_daily,
            },
        )

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
