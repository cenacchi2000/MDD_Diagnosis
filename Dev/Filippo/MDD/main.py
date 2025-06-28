import asyncio
import uuid
import sqlite3
import datetime

import BeckDepression
import bpi_inventory
import central_sensitization
import dass21_assessment
import eq5d5l_assessment
import oswestry_disability_index
import pain_catastrophizing
import pittsburgh_sleep


async def robot_say(text: str):
    """Speak via TTS with console fallback."""
    print(f"[Ameca]: {text}")
    try:
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass


async def robot_listen() -> str:
    """Listen for a response via console input."""
    return input("Your response: ").strip()

def generate_patient_id():
    return f"PAT-{uuid.uuid4().hex[:8]}"

async def collect_demographics():
    await robot_say("Welcome to the Pain & Mood Assessment System")
    patient_id = input("Enter patient ID (or press Enter to auto-generate): ").strip()
    if not patient_id:
        patient_id = generate_patient_id()
        print(f"Generated ID: {patient_id}")

    date = datetime.date.today().strftime("%d/%m/%Y")

    await robot_say("Please tell me your last name")
    name_last = await robot_listen()

    await robot_say("What is your first name?")
    name_first = await robot_listen()

    await robot_say(
        f"Hi {name_first}, nice to meet you. Today we will do a short interview to understand how you are feeling. Can I proceed with the assessment?"
    )
    proceed = (await robot_listen()).lower()
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
    marital_status = await robot_listen()

    await robot_say("Highest grade completed, enter 0 to 16 or M.A./M.S.")
    education = await robot_listen()

    await robot_say("Professional degree if any")
    degree = await robot_listen()

    await robot_say("Current occupation")
    occupation = await robot_listen()

    await robot_say("Spouse occupation if any")
    spouse_occupation = await robot_listen()

    await robot_say("Job status: 1 full time, 2 part time, 3 homemaker, 4 retired, 5 unemployed, 6 other")
    job_status = await robot_listen()

    await robot_say("How many months since diagnosis?")
    diagnosis_time = await robot_listen()

    await robot_say("Pain due to present disease? 1 yes, 2 no, 3 uncertain")
    disease_pain = await robot_listen()

    await robot_say("Was pain a symptom at diagnosis? 1 yes, 2 no, 3 uncertain")
    pain_symptom = await robot_listen()

    await robot_say("Surgery in the past month? 1 yes, 2 no")
    surgery = await robot_listen()

    if surgery == "1":
        await robot_say("What kind of surgery?")
        surgery_type = await robot_listen()
    else:
        surgery_type = ""

    await robot_say("Experienced pain other than minor types last week? 1 yes, 2 no")
    other_pain = await robot_listen()

    await robot_say("Taken pain medication in the last 7 days? 1 yes, 2 no")
    pain_med_week = await robot_listen()

    await robot_say("Do you need daily pain medication? 1 yes, 2 no")
    pain_med_daily = await robot_listen()

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
    conn = sqlite3.connect("patient_responses.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_demographics (
            patient_id TEXT PRIMARY KEY,
            date TEXT,
            name_last TEXT,
            name_first TEXT,
            name_middle TEXT,
            phone TEXT,
            sex TEXT,
            dob TEXT,
            marital_status TEXT,
            education TEXT,
            degree TEXT,
            occupation TEXT,
            spouse_occupation TEXT,
            job_status TEXT,
            diagnosis_time TEXT,
            disease_pain TEXT,
            pain_symptom TEXT,
            surgery TEXT,
            surgery_type TEXT,
            other_pain TEXT,
            pain_med_week TEXT,
            pain_med_daily TEXT
        )
    ''')
    cursor.execute('''
        INSERT OR REPLACE INTO patient_demographics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (patient_id, *data.values()))
    conn.commit()
    conn.close()

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
    print("\n✅ All assessments completed.")

if __name__ == "__main__":
    asyncio.run(main())
