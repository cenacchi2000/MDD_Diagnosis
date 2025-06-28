# Central Sensitization Inventory (CSI) and Worksheet Script
import asyncio
import datetime
import os
import sys
import uuid

sys.path.append(os.path.dirname(__file__))
from remote_storage import send_to_server
from speech_utils import robot_say, robot_listen





def get_patient_id() -> str:
    """Retrieve patient ID from the environment or auto-generate."""
    pid = os.environ.get("patient_id")
    if not pid:
        pid = f"PAT-{uuid.uuid4().hex[:8]}"
    return pid

def timestamp():
    return datetime.datetime.now().isoformat()


csi_questions = [
    "I feel tired and unrefreshed when I wake from sleeping.",
    "My muscles feel stiff and achy.",
    "I have anxiety attacks.",
    "I grind or clench my teeth.",
    "I have problems with diarrhea and/or constipation.",
    "I need help in performing my daily activities.",
    "I am sensitive to bright lights.",
    "I get tired very easily when I am physically active.",
    "I feel pain all over my body.",
    "I have headaches.",
    "I feel discomfort in my bladder and/or burning when I urinate.",
    "I do not sleep well.",
    "I have difficulty concentrating.",
    "I have skin problems such as dryness, itchiness, or rashes.",
    "Stress makes my physical symptoms get worse.",
    "I feel sad or depressed.",
    "I have low energy.",
    "I have muscle tension in my neck and shoulders.",
    "I have pain in my jaw.",
    "Certain smells, such as perfumes, make me feel dizzy and nauseated.",
    "I have to urinate frequently.",
    "My legs feel uncomfortable and restless when I am trying to sleep at night.",
    "I have difficulty remembering things.",
    "I suffered trauma as a child.",
    "I have pain in my pelvic area."
]

csi_worksheet = [
    "Restless Leg Syndrome",
    "Chronic Fatigue Syndrome",
    "Fibromyalgia",
    "Temporomandibular Joint Disorder",
    "Migraine or tension headaches",
    "Irritable Bowel Syndrome",
    "Multiple Chemical Sensitivities",
    "Neck injury (including whiplash)",
    "Anxiety or panic attacks",
    "Depression"
]

score_map = {
    "never": 0,
    "rarely": 1,
    "sometimes": 2,
    "often": 3,
    "always": 4
}

async def run_csi_inventory():
    patient_id = get_patient_id()
    await robot_say("Starting Central Sensitization Inventory (CSI) Part A...")
    total = 0
    for i, question in enumerate(csi_questions):
        await robot_say(f"Q{i+1}: {question}")
        await robot_say("Answer with: Never, Rarely, Sometimes, Often, Always")

        while True:
            ans = (await robot_listen()).lower()
            if ans in score_map:
                score = score_map[ans]
                await robot_say("Thank you.")
                break
            await robot_say("Invalid answer. Please use: Never, Rarely, Sometimes, Often, Always")

        total += score
        send_to_server(
            'responses_csi',
            patient_id=patient_id,
            timestamp=timestamp(),
            question_number=i + 1,
            question_text=question,
            answer=ans.title(),
            score=score,
        )

    await robot_say(f"Your total CSI score is: {total}")
    if total < 30:
        level = "Subclinical"
    elif total < 40:
        level = "Mild"
    elif total < 50:
        level = "Moderate"
    elif total < 60:
        level = "Severe"
    else:
        level = "Extreme"
    await robot_say(f"This corresponds to: {level} CSP involvement.")

async def run_csi_worksheet():
    patient_id = get_patient_id()
    await robot_say("Now beginning Part B: Medical history worksheet...")
    for condition in csi_worksheet:
        await robot_say(f"Are you familiar with {condition}? (yes/no)")
        knows = (await robot_listen()).lower()
        await robot_say("Thank you.")
        if knows == "no":
            await robot_say(f"Explaining {condition}...")
            await robot_say(f"{condition} is a health condition potentially related to chronic pain.")
            diagnosed = "no"
            year = "N/A"
        else:
            await robot_say(f"Have you been diagnosed with {condition}? (yes/no)")
            diagnosed = (await robot_listen()).lower()
            await robot_say("Thank you.")
            if diagnosed == "yes":
                await robot_say("In what year were you diagnosed?")
                year = await robot_listen()
                await robot_say("Thank you.")
            else:
                year = "N/A"

        send_to_server(
            'worksheet_csi',
            patient_id=patient_id,
            timestamp=timestamp(),
            condition=condition,
            knows_about=knows,
            diagnosed=diagnosed,
            year_diagnosed=year,
        )

    await robot_say("Session completed.")

async def main():
    await run_csi_inventory()
    await run_csi_worksheet()

if __name__ == "__main__":
    asyncio.run(main())
