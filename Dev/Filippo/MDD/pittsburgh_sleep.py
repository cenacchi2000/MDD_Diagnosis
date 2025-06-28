# Pittsburgh Sleep Quality Index (PSQI) implementation script
import asyncio
import datetime
import sqlite3
import uuid
from typing import Literal

# Initialize DB connection
conn = sqlite3.connect("patient_responses.db")
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses_psqi (
        patient_id TEXT,
        timestamp TEXT,
        question_number TEXT,
        question_text TEXT,
        answer TEXT,
        score INTEGER
    )
''')
conn.commit()

async def robot_say(text):
    print(f"\n[Ameca]: {text}")

async def robot_listen():
    return input("Your response: ").strip()

def get_timestamp():
    return datetime.datetime.now().isoformat()

def get_patient_id():
    pid = input("Enter patient identifier (or press Enter to generate one): ").strip()
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
        print(f"Generated Patient ID: {pid}")
    return pid

# Map responses to scores as per PSQI guidance
frequency_score = {
    "not during the past month": 0,
    "less than once a week": 1,
    "once or twice a week": 2,
    "three or more times a week": 3
}

problem_score = {
    "no problem at all": 0,
    "only a very slight problem": 1,
    "somewhat of a problem": 2,
    "a very big problem": 3
}

rating_score = {
    "very good": 0,
    "fairly good": 1,
    "fairly bad": 2,
    "very bad": 3
}

async def ask_and_store(patient_id, qnum, text, score_map=None):
    await robot_say(text)
    ans = await robot_listen().lower()
    score = score_map[ans] if score_map and ans in score_map else -1
    cursor.execute('''INSERT INTO responses_psqi VALUES (?, ?, ?, ?, ?, ?)''',
                   (patient_id, get_timestamp(), qnum, text, ans.title(), score))
    conn.commit()
    return score

async def run_psqi():
    patient_id = get_patient_id()
    await robot_say("Starting Pittsburgh Sleep Quality Index (PSQI)")

    # Part 1: Raw numeric entries
    await robot_say("Enter time values in 24h format (e.g., 23:30) or hours as numbers.")
    bedtime = await ask_and_store(patient_id, "1", "What time have you usually gone to bed at night?")
    latency = int(await robot_listen())  # minutes to fall asleep
    cursor.execute('''INSERT INTO responses_psqi VALUES (?, ?, ?, ?, ?, ?)''',
                   (patient_id, get_timestamp(), "2", "How long to fall asleep in minutes:", str(latency), -1))
    waketime = await ask_and_store(patient_id, "3", "What time have you usually gotten up in the morning?")
    sleep_hours = float(await robot_listen())
    cursor.execute('''INSERT INTO responses_psqi VALUES (?, ?, ?, ?, ?, ?)''',
                   (patient_id, get_timestamp(), "4", "How many hours of actual sleep per night:", str(sleep_hours), -1))
    conn.commit()

    # Part 2: Disturbance checklist (5a–j)
    disturbance_sum = 0
    for i, disturbance in enumerate([
        "5a. Cannot get to sleep within 30 minutes",
        "5b. Wake up in the middle of the night or early morning",
        "5c. Have to get up to use the bathroom",
        "5d. Cannot breathe comfortably",
        "5e. Cough or snore loudly",
        "5f. Feel too cold",
        "5g. Feel too hot",
        "5h. Have bad dreams",
        "5i. Have pain",
        "5j. Other reason(s), describe"
    ], start=5):
        score = await ask_and_store(patient_id, str(i), disturbance, frequency_score)
        if score != -1:
            disturbance_sum += score

    # Questions 6–9
    med_use = await ask_and_store(patient_id, "6", "How often have you taken medicine to help you sleep?", frequency_score)
    trouble_awake = await ask_and_store(patient_id, "7", "Trouble staying awake (e.g., driving, eating, social)?", frequency_score)
    enthusiasm = await ask_and_store(patient_id, "8", "How much of a problem has lack of enthusiasm been?", problem_score)
    subjective_quality = await ask_and_store(patient_id, "9", "Rate your sleep quality overall:", rating_score)

    # Component scoring based on rules
    comp1 = rating_score.get(subjective_quality, 0)
    comp2_score = 0
    if latency <= 15: latency_score = 0
    elif latency <= 30: latency_score = 1
    elif latency <= 60: latency_score = 2
    else: latency_score = 3

    latency_freq = await ask_and_store(patient_id, "5a (recheck)", "Frequency of taking more than 30 min to fall asleep:", frequency_score)
    comp2_sum = latency_score + latency_freq
    if comp2_sum == 0: comp2_score = 0
    elif comp2_sum <= 2: comp2_score = 1
    elif comp2_sum <= 4: comp2_score = 2
    else: comp2_score = 3

    comp3_score = 0 if sleep_hours > 7 else 1 if sleep_hours > 6 else 2 if sleep_hours > 5 else 3

    # Bed and wake time for sleep efficiency
    bed_hour = int(bedtime.split(':')[0]) + int(bedtime.split(':')[1]) / 60
    wake_hour = int(waketime.split(':')[0]) + int(waketime.split(':')[1]) / 60
    time_in_bed = (wake_hour - bed_hour + 24) % 24
    efficiency = (sleep_hours / time_in_bed) * 100 if time_in_bed > 0 else 0
    if efficiency > 85: comp4_score = 0
    elif efficiency >= 75: comp4_score = 1
    elif efficiency >= 65: comp4_score = 2
    else: comp4_score = 3

    if disturbance_sum == 0: comp5_score = 0
    elif disturbance_sum <= 9: comp5_score = 1
    elif disturbance_sum <= 18: comp5_score = 2
    else: comp5_score = 3

    comp6_score = med_use

    daytime_sum = trouble_awake + enthusiasm
    if daytime_sum == 0: comp7_score = 0
    elif daytime_sum <= 2: comp7_score = 1
    elif daytime_sum <= 4: comp7_score = 2
    else: comp7_score = 3

    global_score = sum([comp1, comp2_score, comp3_score, comp4_score, comp5_score, comp6_score, comp7_score])

    await robot_say(f"Your global PSQI score is: {global_score} (0–21). Higher scores = worse sleep quality.")

if __name__ == "__main__":
    asyncio.run(run_psqi())
