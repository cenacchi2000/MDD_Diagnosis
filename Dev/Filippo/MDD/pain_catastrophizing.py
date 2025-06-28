# Pain Catastrophizing Scale (PCS) – Full Implementation with Scoring and DB Storage

import sqlite3
import datetime
import uuid
import asyncio

# Initialize or connect to shared database
conn = sqlite3.connect("patient_responses.db")
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses_pcs (
        patient_id TEXT,
        timestamp TEXT,
        question_number INTEGER,
        question_text TEXT,
        score INTEGER
    )
''')
conn.commit()

# Patient ID handling
patient_id = input("Enter patient identifier (or press Enter to generate one): ").strip()
if not patient_id:
    patient_id = f"PAT-{uuid.uuid4().hex[:8]}"
    print(f"Generated Patient ID: {patient_id}")

# PCS questions
pcs_questions = [
    "I worry all the time about whether the pain will end.",
    "I feel I can’t go on.",
    "It’s terrible and I think it’s never going to get any better.",
    "It’s awful and I feel that it overwhelms me.",
    "I feel I can’t stand it anymore.",
    "I become afraid that the pain will get worse.",
    "I keep thinking of other painful events.",
    "I anxiously want the pain to go away.",
    "I can’t seem to keep it out of my mind.",
    "I keep thinking about how much it hurts.",
    "I keep thinking about how badly I want the pain to stop.",
    "There’s nothing I can do to reduce the intensity of the pain.",
    "I wonder whether something serious may happen."
]

rating_scale = {
    "0": "Not at all",
    "1": "To a slight degree",
    "2": "To a moderate degree",
    "3": "To a great degree",
    "4": "All the time"
}

def current_timestamp():
    return datetime.datetime.now().isoformat()

async def robot_say(text):
    print(f"\n[Ameca]: {text}")

async def robot_listen():
    return input("Your response (0-4): ").strip()

async def run_pcs():
    total_score = 0
    await robot_say("Welcome to the Pain Catastrophizing Scale questionnaire. Please answer each item based on how you feel when you're in pain.")
    await robot_say("The scale is: 0 = Not at all, 1 = Slight degree, 2 = Moderate degree, 3 = Great degree, 4 = All the time.")

    for i, question in enumerate(pcs_questions):
        await robot_say(f"Q{i+1}: {question}")

        while True:
            response = await robot_listen()
            if response in rating_scale:
                score = int(response)
                break
            await robot_say("Invalid response. Please enter a number from 0 to 4.")

        total_score += score
        cursor.execute('''
            INSERT INTO responses_pcs (patient_id, timestamp, question_number, question_text, score)
            VALUES (?, ?, ?, ?, ?)
        ''', (patient_id, current_timestamp(), i + 1, question, score))
        conn.commit()

        await robot_say(f"Recorded response: {rating_scale[response]} (Score: {score})")

    await robot_say(f"\nThank you. Your total PCS score is {total_score}.")
    if total_score >= 30:
        await robot_say("This indicates a clinically relevant level of pain catastrophizing.")
    else:
        await robot_say("Your score suggests a lower tendency toward pain catastrophizing.")

if __name__ == "__main__":
    asyncio.run(run_pcs())
