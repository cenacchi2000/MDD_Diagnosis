# Beck Depression Inventory (BDI) - Integrated with shared database (patient_responses.db)

import datetime
import asyncio
import sqlite3
import uuid
import os

# Setup shared database
conn = sqlite3.connect("patient_responses.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses_bdi (
        patient_id TEXT,
        timestamp TEXT,
        question_number INTEGER,
        question_title TEXT,
        answer TEXT,
        score INTEGER
    )
''')
conn.commit()

# Generate patient ID, preferring environment variable
patient_id = os.environ.get("patient_id")
if not patient_id:
    patient_id = input("Enter patient identifier (or press Enter to generate one): ").strip()
    if not patient_id:
        patient_id = f"PAT-{uuid.uuid4().hex[:8]}"
        print(f"Generated Patient ID: {patient_id}")

async def robot_say(text: str):
    """Speak through TTS and print as fallback."""
    print(f"[Ameca says]: {text}\n")
    try:
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass

async def robot_listen() -> str:
    return input("Your response (0, 1, 2, 3): ").strip()

async def store_response_to_db(question_number: int, question_title: str, answer: str, score: int):
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO responses_bdi (patient_id, timestamp, question_number, question_title, answer, score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (patient_id, timestamp, question_number, question_title, answer, score))
    conn.commit()
    print(f"[DB] Q{question_number} [{question_title}] → '{answer}' (Score: {score})")

bdi_questions = [
    ("Sadness", ["I do not feel sad.", "I feel sad.", "I am sad all the time and can't snap out of it.", "I am so sad and unhappy that I can't stand it."]),
    ("Pessimism", ["I am not particularly discouraged about the future.", "I feel discouraged about the future.", "I feel I have nothing to look forward to.", "I feel the future is hopeless and that things cannot be done."]),
    ("Failure", ["I do not feel like a failure.", "I feel I have failed more than the average person.", "As I look back on my life, all I can see is a lot of failures.", "I feel I am a complete failure as a person."]),
    ("Satisfaction", ["I get as much satisfaction out of things as I used to.", "I don’t enjoy things the way I used to.", "I don't get real satisfaction out of anything anymore.", "I am dissatisfied or bored with everything."]),
    ("Guilt", ["I don’t feel particularly guilty.", "I feel guilty a good part of the time.", "I feel quite guilty most of the time.", "I feel guilty all of the time."]),
    ("Punishment", ["I don’t feel I am being punished.", "I feel I may be punished.", "I expect to be punished.", "I feel I am being punished."]),
    ("Self-disappointment", ["I don’t feel disappointed in myself.", "I am disappointed in myself.", "I am disgusted with myself.", "I hate myself."]),
    ("Self-criticism", ["I don’t feel I am any worse than anybody else.", "I am critical of myself for my weakness or mistakes.", "I blame myself all the time for my faults.", "I blame myself for everything bad that happens."]),
    ("Suicidal thoughts", ["I don’t have any thoughts of killing myself.", "I have thoughts of killing myself, but I would not carry them out.", "I would like to kill myself.", "I would kill myself if I had the chance."]),
    ("Crying", ["I don’t cry any more than usual.", "I cry more now than I used to.", "I cry all the time now.", "I used to be able to cry, but now I can’t cry even though I want to."]),
    ("Irritability", ["I am no more irritated by things than I ever was.", "I am slightly more irritated now than usual.", "I am quite annoyed or irritated a good deal of the time.", "I feel irritated all the time."]),
    ("Social withdrawal", ["I have not lost interest in other people.", "I am less interested in other people than I used to be.", "I have lost most of my interest in other people.", "I have lost all of my interest in other people."]),
    ("Decision making", ["I make decisions about as well as I ever could.", "I put off making decisions more than I used to.", "I have greater difficulty in making decisions more than I used to.", "I can't make decisions at all anymore."]),
    ("Body image", ["I don’t feel that I look any worse than I used to.", "I am worried that I am looking old or unattractive.", "I feel there are permanent changes in my appearance that make me look unattractive.", "I believe that I look ugly."]),
    ("Work capacity", ["I can work about as well as before.", "It takes an extra effort to get started at doing something.", "I have to push myself very hard to do anything.", "I can't do any work at all."]),
    ("Sleep", ["I can sleep as well as usual.", "I don’t sleep as well as I used to.", "I wake up 1–2 hours earlier than usual and find it hard to get back to sleep.", "I wake up several hours earlier than I used to and cannot get back to sleep."]),
    ("Fatigue", ["I don't get more tired than usual.", "I get tired more easily than I used to.", "I get tired from doing almost anything.", "I am too tired to do anything."]),
    ("Appetite", ["My appetite is no worse than usual.", "My appetite is not as good as it used to be.", "My appetite is much worse now.", "I have no appetite at all anymore."]),
    ("Weight loss", ["I haven't lost much weight, if any, lately.", "I have lost more than five pounds.", "I have lost more than ten pounds.", "I have lost more than fifteen pounds."]),
    ("Health concerns", ["I am no more worried about my health than usual.", "I am worried about physical problems like aches, pain, upset stomach or constipation.", "I am very worried about physical problems and it's hard to think of much else.", "I am so worried about my physical problems that I cannot think of anything else."]),
    ("Sexual interest", ["I have not noticed any recent changes in my interest in sex.", "I am less interested in sex than I used to be.", "I have almost no interest in sex.", "I have lost interest in sex completely."])
]

async def run_beck_depression_inventory():
    total_score = 0
    for i, (title, options) in enumerate(bdi_questions):
        await robot_say(f"Question {i+1} - {title}:")
        for idx, opt in enumerate(options):
            print(f"  [{idx}] {opt}")

        valid = False
        while not valid:
            response = await robot_listen()
            if response in ["0", "1", "2", "3"]:
                score = int(response)
                valid = True
                await robot_say("Thank you.")
            else:
                await robot_say("Please enter a valid response: 0, 1, 2, or 3.")

        total_score += score
        await store_response_to_db(i+1, title, options[score], score)

    await robot_say(f"You have completed the questionnaire. Your total score is {total_score}.")
    category = interpret_score(total_score)
    await robot_say(f"According to the Beck Depression Inventory, this corresponds to: {category}")
    return f"Total score: {total_score} – {category}"

def interpret_score(score: int) -> str:
    if score <= 10:
        return "These ups and downs are considered normal."
    elif score <= 16:
        return "Mild mood disturbances."
    elif score <= 20:
        return "Borderline clinical depression."
    elif score <= 30:
        return "Moderate depression."
    elif score <= 40:
        return "Severe depression."
    else:
        return "Extreme depression."

if __name__ == "__main__":
    asyncio.run(run_beck_depression_inventory())
