# eq5d5l_assessment.py
import sqlite3
import uuid
import datetime
import asyncio
import os

# Initialize DB
conn = sqlite3.connect("patient_responses.db")
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses_eq5d5l (
        patient_id TEXT,
        timestamp TEXT,
        dimension TEXT,
        level INTEGER,
        health_state_code TEXT,
        vas_score INTEGER
    )
''')
conn.commit()

# EQ-5D-5L dimension descriptions
eq5d5l_dimensions = {
    "Mobility": [
        "I have no problems in walking about",
        "I have slight problems in walking about",
        "I have moderate problems in walking about",
        "I have severe problems in walking about",
        "I am unable to walk about"
    ],
    "Self-Care": [
        "I have no problems washing or dressing myself",
        "I have slight problems washing or dressing myself",
        "I have moderate problems washing or dressing myself",
        "I have severe problems washing or dressing myself",
        "I am unable to wash or dress myself"
    ],
    "Usual Activities": [
        "I have no problems doing my usual activities",
        "I have slight problems doing my usual activities",
        "I have moderate problems doing my usual activities",
        "I have severe problems doing my usual activities",
        "I am unable to do my usual activities"
    ],
    "Pain/Discomfort": [
        "I have no pain or discomfort",
        "I have slight pain or discomfort",
        "I have moderate pain or discomfort",
        "I have severe pain or discomfort",
        "I have extreme pain or discomfort"
    ],
    "Anxiety/Depression": [
        "I am not anxious or depressed",
        "I am slightly anxious or depressed",
        "I am moderately anxious or depressed",
        "I am severely anxious or depressed",
        "I am extremely anxious or depressed"
    ]
}

async def robot_say(msg: str):
    """Speak via TTS with console fallback."""
    print(f"\n[Ameca]: {msg}")
    try:
        system.messaging.post("tts_say", [msg, "eng"])
    except Exception:
        pass

async def robot_listen() -> str:
    return input("Your response: ").strip()

def get_timestamp():
    return datetime.datetime.now().isoformat()

async def collect_patient_id():
    pid = os.environ.get("patient_id")
    if not pid:
        pid = input("Enter patient ID (or press Enter to auto-generate): ").strip()
        if not pid:
            pid = f"PAT-{uuid.uuid4().hex[:8]}"
            print(f"[Info] Generated Patient ID: {pid}")
    return pid

async def run_eq5d5l_questionnaire():
    patient_id = await collect_patient_id()
    levels = []
    health_state_code = ""

    await robot_say("We will begin the EQ-5D-5L assessment. For each question, respond with 1 to 5.")

    for dimension, statements in eq5d5l_dimensions.items():
        await robot_say(f"{dimension} – please select one of the following:")
        for i, statement in enumerate(statements, 1):
            print(f"  [{i}] {statement}")

        while True:
            response = await robot_listen()
            if response.isdigit() and 1 <= int(response) <= 5:
                level = int(response)
                levels.append(level)
                health_state_code += str(level)
                await robot_say("Thank you.")
                cursor.execute('''
                    INSERT INTO responses_eq5d5l (patient_id, timestamp, dimension, level, health_state_code, vas_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (patient_id, get_timestamp(), dimension, level, None, None))
                conn.commit()
                break
            else:
                await robot_say("Please enter a number between 1 and 5.")

    await robot_say("Now, rate your health today on a scale from 0 to 100.")
    while True:
        vas_input = await robot_listen()
        if vas_input.isdigit() and 0 <= int(vas_input) <= 100:
            vas_score = int(vas_input)
            await robot_say("Thank you.")
            break
        else:
            await robot_say("Enter a valid number between 0 and 100.")

    # Update DB with health state code and VAS for each row for this patient
    cursor.execute('''
        UPDATE responses_eq5d5l
        SET health_state_code = ?, vas_score = ?
        WHERE patient_id = ?
    ''', (health_state_code, vas_score, patient_id))
    conn.commit()

    await robot_say(f"✅ EQ-5D-5L complete. Your health state code is: {health_state_code}")
    await robot_say(f"Your self-rated health (VAS) score is: {vas_score}")

    # Optional: placeholder for utility scoring (requires national dataset e.g. UK, AU)
    utility = calculate_placeholder_utility(levels)
    await robot_say(f"Estimated utility index (placeholder): {utility:.3f}")

def calculate_placeholder_utility(levels):
    # Simple pseudo-utility calculator (for demo purposes)
    decrement = sum((level - 1) * 0.1 for level in levels)
    utility = max(1.0 - decrement, 0.0)
    return utility

if __name__ == "__main__":
    asyncio.run(run_eq5d5l_questionnaire())
