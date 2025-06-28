import sqlite3
import uuid
import datetime
import os

# Connect to or create database
conn = sqlite3.connect("patient_responses.db")
cursor = conn.cursor()

# Create ODI table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses_odi (
        patient_id TEXT,
        timestamp TEXT,
        question_number INTEGER,
        question_text TEXT,
        selected_option TEXT,
        score INTEGER
    )
''')
conn.commit()

# Generate patient ID or accept user-defined one
patient_id = os.environ.get("patient_id")
if not patient_id:
    patient_id = input("Enter patient identifier (or press enter to generate one): ").strip()
    if not patient_id:
        patient_id = f"PAT-{uuid.uuid4().hex[:8]}"
        print(f"Generated Patient ID: {patient_id}")

def get_timestamp():
    return datetime.datetime.now().isoformat()

async def robot_say(text: str):
    """Speak text via TTS with console fallback."""
    print(f"[Ameca]: {text}")
    try:
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass

async def robot_listen() -> str:
    return input("Select the number that best applies (0–5): ").strip()

# Questionnaire structure
questions = [
    ("PAIN INTENSITY", [
        "I can tolerate the pain I have without having to use pain killers",
        "The pain is bad but I manage without taking pain killers",
        "Pain killers give complete relief from pain",
        "Pain killers give moderate relief from pain",
        "Pain killers give very little relief from pain",
        "Pain killers have no effect on the pain and I do not use them"
    ]),
    ("PERSONAL CARE", [
        "I can look after myself normally without causing extra pain",
        "I can look after myself normally but it causes extra pain",
        "It is painful to look after myself and I am slow and careful",
        "I need some help but manage most of my personal care",
        "I need help every day in most aspects of self care",
        "I don’t get dressed, I wash with difficulty and stay in bed"
    ]),
    ("LIFTING", [
        "I can lift heavy weights without extra pain",
        "I can lift heavy weights but it gives extra pain",
        "Pain prevents me from lifting heavy weights off the floor, but I can manage if they are on a table",
        "Pain prevents me from lifting heavy weights, but I can manage light to medium weights",
        "I can lift very light weights",
        "I cannot lift or carry anything at all"
    ]),
    ("WALKING", [
        "Pain does not prevent me walking any distance",
        "Pain prevents me walking more than one mile",
        "Pain prevents me walking more than ½ mile",
        "Pain prevents me walking more than ¼ mile",
        "I can only walk using a stick or crutches",
        "I am in bed most of the time and have to crawl to the toilet"
    ]),
    ("SITTING", [
        "I can sit in any chair as long as I like",
        "I can only sit in my favorite chair as long as I like",
        "Pain prevents me from sitting more than one hour",
        "Pain prevents me from sitting more than ½ hour",
        "Pain prevents me from sitting more than 10 minutes",
        "Pain prevents me from sitting at all"
    ]),
    ("STANDING", [
        "I can stand as long as I want without extra pain",
        "I can stand as long as I want but it gives me extra pain",
        "Pain prevents me from standing for more than one hour",
        "Pain prevents me from standing for more than 30 minutes",
        "Pain prevents me from standing for more than 10 minutes",
        "Pain prevents me from standing at all"
    ]),
    ("SLEEPING", [
        "Pain does not prevent me from sleeping well",
        "I can sleep well only by using medication",
        "Even when I take medication, I have less than 6 hrs sleep",
        "Even when I take medication, I have less than 4 hrs sleep",
        "Even when I take medication, I have less than 2 hrs sleep",
        "Pain prevents me from sleeping at all"
    ]),
    ("SOCIAL LIFE", [
        "My social life is normal and gives me no extra pain",
        "My social life is normal but increases the degree of pain",
        "Pain has no significant effect apart from limiting energetic interests",
        "Pain has restricted my social life and I don’t go out as often",
        "Pain has restricted my social life to my home",
        "I have no social life because of pain"
    ]),
    ("TRAVELLING", [
        "I can travel anywhere without extra pain",
        "I can travel anywhere but it gives me extra pain",
        "Pain is bad, but I manage journeys over 2 hours",
        "Pain restricts me to journeys of less than 1 hour",
        "Pain restricts me to short necessary journeys under 30 minutes",
        "Pain prevents me from traveling except to the doctor or hospital"
    ]),
    ("EMPLOYMENT / HOMEMAKING", [
        "My normal job activities do not cause pain",
        "My normal job activities increase pain, but I can still perform all duties",
        "I can perform most duties, but pain prevents me from strenuous tasks",
        "Pain prevents me from doing anything but light duties",
        "Pain prevents me from doing even light duties",
        "Pain prevents me from performing any job or chores"
    ])
]

def interpret_score(total_score):
    if total_score <= 4:
        return "No disability"
    elif total_score <= 14:
        return "Mild disability"
    elif total_score <= 24:
        return "Moderate disability"
    elif total_score <= 34:
        return "Severe disability"
    else:
        return "Completely disabled"

async def run_odi():
    total_score = 0
    for i, (title, options) in enumerate(questions, start=1):
        await robot_say(f"Q{i}. {title}")
        for idx, opt in enumerate(options):
            print(f"  [{idx}] {opt}")

        while True:
            user_input = await robot_listen()
            if user_input.isdigit() and 0 <= int(user_input) < len(options):
                score = int(user_input)
                await robot_say("Thank you.")
                break
            await robot_say("Invalid input. Please select a number between 0 and 5.")

        total_score += score
        cursor.execute('''
            INSERT INTO responses_odi (patient_id, timestamp, question_number, question_text, selected_option, score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (patient_id, get_timestamp(), i, title, options[score], score))
        conn.commit()

    await robot_say(f"ODI Complete. Total Score: {total_score} / 50")
    level = interpret_score(total_score)
    await robot_say(f"Disability Level: {level}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_odi())
