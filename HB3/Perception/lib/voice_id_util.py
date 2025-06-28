import os
import json
from time import monotonic
from collections import deque

import numpy as np

VOICE_ID_THRESHOLD: float = 0.3
"""cosine similarity threshold for voice id comparison"""

MAX_LENGTH: int = 3
"""Max number of voice ids to buffer"""

JSON_FILE_PATH: str = "/var/opt/tritium/personal_data/known_voice_ids.json"
"""File path where the known voices are stored on disk"""

UNKNOWN_SPEAKER_TOKEN: str = "Unidentified Speaker"
"""Token used to represent unknown speaker"""


_KNOWN_VOICE_IDS: dict[str, deque[np.ndarray]] = {}
"""Known voices stored in memory."""

_LAST_HEARD: deque[np.ndarray] = deque(maxlen=MAX_LENGTH)
"""Buffer for the last N voices heard"""


def save_known_voice_ids():
    cache: dict[str, list[float]] = {}
    for name, ids in _KNOWN_VOICE_IDS.items():
        cache[name] = _mean_embedding(ids).tolist()

    os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)
    with open(JSON_FILE_PATH, "w") as f:
        json.dump(cache, f)


def load_know_voice_ids():
    try:
        with open(JSON_FILE_PATH, "r") as f:
            cache = json.load(f)
        for name, id in cache.items():
            update_know_voice(name, np.array(id))
        log.info(f"{len(cache)} voice ids loaded")
    except IOError:
        log.warning("No known voices loaded")


def _mean_embedding(embeddings: deque[np.ndarray]) -> np.ndarray:
    return np.array(sum(embeddings) / len(embeddings))


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_voice_id_head() -> np.ndarray | None:
    return _LAST_HEARD[-1] if _LAST_HEARD else None


def update_know_voice(speaker_name: str, voice_id: np.ndarray):
    if speaker_name in _KNOWN_VOICE_IDS:
        _KNOWN_VOICE_IDS[speaker_name].append(voice_id)
    else:
        _KNOWN_VOICE_IDS[speaker_name] = deque([voice_id], maxlen=MAX_LENGTH)
    save_known_voice_ids()


def get_known_voices() -> list[str]:
    return list(_KNOWN_VOICE_IDS.keys())


def remove_voice(speaker_name: str):
    try:
        _KNOWN_VOICE_IDS.pop(speaker_name)
    except KeyError:
        raise RuntimeError(f"{speaker_name} is not a known voice")
    save_known_voice_ids()


def process_voice_id(voice_ids: list[list[float]]) -> str:
    start_time = monotonic()

    rval: str | None = None
    for embedding in voice_ids:  # right now only one embedding is returned by SP

        similarity_trashed = VOICE_ID_THRESHOLD
        emb = np.array(embedding)

        # populated _LAST_HEARD
        _LAST_HEARD.append(emb)

        for name, known_ids in _KNOWN_VOICE_IDS.items():
            if not known_ids:
                continue
            mean_embedding = _mean_embedding(known_ids)
            similarity = _cosine_similarity(emb, mean_embedding)
            log.info(f"Voice similarity with {name}: {similarity}")
            if similarity > similarity_trashed:
                rval = name
                similarity_trashed = similarity
    rval = UNKNOWN_SPEAKER_TOKEN if rval is None else rval
    log.info(f"process_voice_id() took: {monotonic() - start_time} seconds")
    return rval