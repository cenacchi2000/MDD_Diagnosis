# Script to administer the full Brief Pain Inventory (BPI), auto-generate patient ID, and store structured answers
# in SQLite (patient_responses.db)

import asyncio
import datetime
import os
import sys
import uuid

sys.path.append(os.path.dirname(__file__))
from remote_storage import send_to_server


def get_patient_id() -> str:
    """Retrieve patient ID from environment or prompt the user."""
    pid = os.environ.get("patient_id")
    if not pid:
        pid = input("Enter patient identifier (or press enter to generate one): ").strip()
        if not pid:
            pid = f"PAT-{uuid.uuid4().hex[:8]}"
            print(f"Generated Patient ID: {pid}")
    return pid



async def robot_say(text: str):
    print(f"[Ameca]: {text}")
    try:
        system.messaging.post("tts_say", [text, "eng"])
    except Exception:
        pass

async def robot_listen() -> str:
    return input("Your response: ").strip()

# Long-form BPI Questions — simplified text w/ freeform or numeric entry
bpi_questions = [
    "1. Rate your pain at its worst in the last 24 hours (0 = No pain, 10 = Worst imaginable):",
    "2. Rate your pain at its least in the last 24 hours (0 = No pain, 10 = Worst imaginable):",
    "3. Rate your average pain (0 = No pain, 10 = Worst imaginable):",
    "4. Rate your pain right now (0 = No pain, 10 = Worst imaginable):",
    "5a. Do you have pain in more than one location? (Yes/No):",
    "5b. Mark the areas where you feel pain (free description):",
    "6. When did your pain start? (e.g., '1 month ago', '3 days ago'):",
    "7. What causes or increases your pain? (free response):",
    "8. What relieves your pain? (free response):",
    "9a. In the last 24 hours, how much relief have pain treatments given you? (0%–100%):",
    "10a. Pain interfered with General Activity (0 = No interference, 10 = Complete interference):",
    "10b. Mood:",
    "10c. Walking ability:",
    "10d. Normal work:",
    "10e. Relations with others:",
    "10f. Sleep:",
    "10g. Enjoyment of life:",
    "11. Are you currently taking pain medications? (Yes/No):",
    "12a. If yes, list your current medications:",
    "12b. How often do you take these medications?:",
    "12c. How well are these medications working?:",
    "13. Have you had any side effects from your pain medications? (Yes/No):",
    "14. List any side effects experienced:",
    "15. Any other comments about your pain or treatment?"
]

# Auto-adjust question numbering (we split compound questions)
async def run_bpi():
    patient_id = get_patient_id()
    for i, question in enumerate(bpi_questions):
        await robot_say(f"{question}")
        response = await robot_listen()
        await robot_say("Thank you.")
        timestamp = datetime.datetime.now().isoformat()

        send_to_server(
            'responses_bpi',
            patient_id=patient_id,
            timestamp=timestamp,
            question_number=i + 1,
            question_text=question,
            response=response,
        )

        print(f"[Saved] Question {i + 1}: {response}")

    await robot_say(f"All responses saved for Patient ID: {patient_id}")

if __name__ == "__main__":
    asyncio.run(run_bpi())
