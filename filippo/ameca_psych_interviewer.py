"""Single-file empathetic PHQ-8 & PCL-C interviewer.

This module is designed to run directly inside the Tritium runtime as a
standalone activity.  It mirrors the Activity pattern used in
``HB3/Chat_Controller.py`` so that the Ameca robot can speak, animate and
update its behaviour over time.

The interviewer walks a user through the PHQ-8 and PCL-C questionnaires,
adds simple empathetic micro‑turns, computes scores and updates a small
persistent coach state to slowly adapt future sessions.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List

# Optional HTTP client for LLM calls.  Fallback to None if requests is not
# available so the file stays self contained.
try:  # pragma: no cover - optional import
    import requests
except Exception:  # pragma: no cover
    requests = None

# ---------------------------------------------------------------------------
# Data & persistence helpers
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
COACH_STATE_FILE = DATA_DIR / "coach_state.json"

DEFAULT_COACH_STATE = {
    "version": 1,
    "follow_up_aggressiveness": 0.35,
    "reflective_ratio": 0.55,
    "pause_probe_threshold": 0.75,
    "smile_coach": 0.1,
    "brow_soothe": 0.15,
}


def load_coach_state() -> Dict[str, Any]:
    if not COACH_STATE_FILE.exists():
        save_coach_state(DEFAULT_COACH_STATE)
    with COACH_STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_coach_state(state: Dict[str, Any]) -> None:
    COACH_STATE_FILE.parent.mkdir(exist_ok=True)
    with COACH_STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Questionnaire banks and scoring utilities
# ---------------------------------------------------------------------------
PHQ8_ITEMS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling/staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself / failure / let family down",
    "Trouble concentrating (reading/watching TV)",
    "Moving/speaking slowly or fidgety/restless more than usual",
]

PCLC_ITEMS = [
    "Intrusive memories/images",
    "Disturbing dreams",
    "Flashbacks",
    "Upset when reminded",
    "Physical reactions when reminded",
    "Avoid thoughts/feelings",
    "Avoid activities/situations",
    "Trouble remembering parts",
    "Loss of interest",
    "Feeling distant",
    "Emotional numbness",
    "Foreshortened future",
    "Sleep trouble",
    "Irritability/anger",
    "Concentration difficulty",
    "Hypervigilance",
    "Startle/jumpy",
]


PHQ_KEYWORDS = {
    "not at all": 0,
    "several days": 1,
    "more than half the days": 2,
    "nearly every day": 3,
}

PCLC_KEYWORDS = {
    "not at all": 1,
    "a little bit": 2,
    "moderately": 3,
    "quite a bit": 4,
    "extremely": 5,
}


def score_phq8(answers: List[int]) -> Dict[str, Any]:
    total = sum(answers)
    if total <= 4:
        severity = "none/minimal"
    elif total <= 9:
        severity = "mild"
    elif total <= 14:
        severity = "moderate"
    elif total <= 19:
        severity = "moderately severe"
    else:
        severity = "severe"
    return {"total": total, "severity": severity}


def score_pclc(answers: List[int]) -> Dict[str, Any]:
    total = sum(answers)
    b = sum(1 for a in answers[0:5] if a >= 3) >= 1
    c = sum(1 for a in answers[5:12] if a >= 3) >= 3
    d = sum(1 for a in answers[12:17] if a >= 3) >= 2
    if total <= 29:
        severity = "low"
    elif total <= 44:
        severity = "moderate"
    else:
        severity = "high"
    return {
        "total": total,
        "clusters": {"B": b, "C": c, "D": d},
        "meets_dsm": b and c and d,
        "severity": severity,
    }


def map_phq8_score(text: str) -> int:
    t = text.strip().lower()
    if t.isdigit():
        return min(max(int(t), 0), 3)
    for k, v in PHQ_KEYWORDS.items():
        if k in t:
            return v
    return 0


def map_pclc_score(text: str) -> int:
    t = text.strip().lower()
    if t.isdigit():
        return min(max(int(t), 1), 5)
    for k, v in PCLC_KEYWORDS.items():
        if k in t:
            return v
    return 1


# ---------------------------------------------------------------------------
# Simple LLM hook
# ---------------------------------------------------------------------------
def llm_reflect(text: str) -> str:
    """Paraphrase a short empathetic reflection via local LLM if available."""
    url = os.getenv("OLLAMA_URL")
    if not url or not requests:
        return f"I hear you. {text.strip()}"
    try:  # pragma: no cover - network call
        payload = {"model": "llama3", "prompt": f"Paraphrase empathetically: {text}"}
        resp = requests.post(f"{url}/api/generate", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", text)
    except Exception:
        return f"I hear you. {text.strip()}"


# ---------------------------------------------------------------------------
# Activity implementation
# ---------------------------------------------------------------------------
class Activity:
    def on_start(self):
        self.coach_state = load_coach_state()
        self.session_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
        self.phase = "intro"
        self.phq8_index = 0
        self.pclc_index = 0
        self.phq8_answers: List[int] = []
        self.pclc_answers: List[int] = []
        self.notes: Dict[str, List[str]] = {"verbal": [], "facial": []}
        self.say(
            "Hello, I'm here to ask a few standard questions about your well-being."
            " I may pause to check in. Is it okay to continue?",
            anim="Animations.dir/System.dir/Chat Expressions.dir/Chat_G2_Happy_1.project",
        )

    def on_stop(self):
        pass

    # Wrapper for speech + facial animation
    def say(self, text: str, anim: str = "Animations.dir/System.dir/Chat Expressions.dir/Chat_G2_Neutral.project"):
        system.messaging.post("play_sequence", anim)
        system.messaging.post("tts_say", [text, "eng"])

    async def on_message(self, channel, message):
        if channel != "speech_recognized":
            return
        user_text = message.get("text") if isinstance(message, dict) else str(message)
        if self.phase == "intro":
            self.phase = "phq8"
            await asyncio.sleep(0.1)
            self.ask_question()
            return

        if self.phase == "phq8":
            score = map_phq8_score(user_text)
            self.phq8_answers.append(score)
            self.phq8_index += 1
            if random.random() < self.coach_state["reflective_ratio"]:
                self.say(llm_reflect(user_text))
            await asyncio.sleep(0.1)
            if self.phq8_index < len(PHQ8_ITEMS):
                self.ask_question()
            else:
                self.phase = "pclc"
                self.ask_question()
            return

        if self.phase == "pclc":
            score = map_pclc_score(user_text)
            self.pclc_answers.append(score)
            self.pclc_index += 1
            if random.random() < self.coach_state["reflective_ratio"]:
                self.say(llm_reflect(user_text))
            await asyncio.sleep(0.1)
            if self.pclc_index < len(PCLC_ITEMS):
                self.ask_question()
            else:
                self.phase = "wrap"
                self.end_session()
            return

    def ask_question(self):
        if self.phase == "phq8":
            q = PHQ8_ITEMS[self.phq8_index]
            self.say(f"{q}. (0 not at all .. 3 nearly every day)")
        elif self.phase == "pclc":
            q = PCLC_ITEMS[self.pclc_index]
            self.say(f"{q}. (1 not at all .. 5 extremely)")

    def end_session(self):
        phq = score_phq8(self.phq8_answers)
        pcl = score_pclc(self.pclc_answers)
        report = {
            "session_id": self.session_id,
            "timestamp": dt.datetime.now().isoformat(),
            "phq8": phq,
            "pclc": pcl,
            "notes": self.notes,
        }
        with (REPORTS_DIR / f"{self.session_id}.json").open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        self.learn_from_session(phq, pcl)
        self.say(
            f"Thank you. Your PHQ-8 score is {phq['total']} and your PCL-C score is {pcl['total']}."
            " This is a screening, not a diagnosis. Please consider talking to a clinician if concerned.",
            anim="Animations.dir/System.dir/Chat Expressions.dir/Chat_G2_Sad_1.project",
        )

    def learn_from_session(self, phq: Dict[str, Any], pcl: Dict[str, Any]):
        state = load_coach_state()
        if phq["total"] > 10 or pcl["total"] > 30:
            state["smile_coach"] = min(state["smile_coach"] + 0.05, 0.5)
            state["brow_soothe"] = min(state["brow_soothe"] + 0.05, 0.5)
        state["reflective_ratio"] = min(state["reflective_ratio"] + 0.01, 0.7)
        save_coach_state(state)

    @system.tick(fps=1)
    def on_tick(self):
        probe("Session Phase", self.phase)
