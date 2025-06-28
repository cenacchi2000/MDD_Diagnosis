import asyncio
import uuid
import sqlite3

import BeckDepression
import bpi_inventory
import central_sensitization
import dass21_assessment
import eq5d5l_assessment
import oswestry_disability_index
import pain_catastrophizing
import pittsburgh_sleep

def generate_patient_id():
    return f"PAT-{uuid.uuid4().hex[:8]}"

def collect_demographics():
    print("\n=== Welcome to the Pain & Mood Assessment System ===\n")
    patient_id = input("Enter patient ID (or press Enter to auto-generate): ").strip()
    if not patient_id:
        patient_id = generate_patient_id()
        print(f"Generated ID: {patient_id}")

    print("\nPlease answer the following demographic questions:\n")

    date = input("Date (DD/MM/YYYY): ")
    name_last = input("Last Name: ")
    name_first = input("First Name: ")
    name_middle = input("Middle Initial (optional): ")
    phone = input("Phone Number: ")
    sex = input("Sex (M/F): ")
    dob = input("Date of Birth (DD/MM/YYYY): ")

    marital_status = input("Marital Status (1=Single, 2=Married, 3=Widowed, 4=Separated/Divorced): ")
    education = input("Highest Grade Completed (0–16 or M.A./M.S.): ")
    degree = input("Professional degree (if any): ")
    occupation = input("Current Occupation: ")
    spouse_occupation = input("Spouse's Occupation (if any): ")
    job_status = input("Job Status (1=FT, 2=PT, 3=Homemaker, 4=Retired, 5=Unemployed, 6=Other): ")
    diagnosis_time = input("How many months since diagnosis?: ")
    disease_pain = input("Pain due to present disease? (1=Yes, 2=No, 3=Uncertain): ")
    pain_symptom = input("Was pain a symptom at diagnosis? (1=Yes, 2=No, 3=Uncertain): ")
    surgery = input("Surgery in past month? (1=Yes, 2=No): ")
    surgery_type = input("If YES, what kind?: ") if surgery == "1" else ""
    other_pain = input("Experienced pain (other than minor types) last week? (1=Yes, 2=No): ")
    pain_med_week = input("Taken pain meds last 7 days? (1=Yes, 2=No): ")
    pain_med_daily = input("Need daily pain meds? (1=Yes, 2=No): ")

    store_demographics(patient_id, {
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
    })

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
    patient_id = collect_demographics()
    await run_all_assessments(patient_id)
    print("\n✅ All assessments completed.")

if __name__ == "__main__":
    asyncio.run(main())
