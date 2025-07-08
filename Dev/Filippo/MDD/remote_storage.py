import os
import json
import sqlite3
from urllib import request

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000/store")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patient_responses.db")


def _store_locally(table: str, data: dict) -> None:
    """Insert ``data`` into the local SQLite database.

    The schema may evolve over time, so this function ensures any missing
    columns are added before inserting the row.  ``data`` values are stored as
    text to keep things simple.
    """

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create the table if it does not yet exist with the current columns
    col_defs = ", ".join(f"{c} TEXT" for c in data)
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table} ({col_defs})")

    # Ensure all columns required for this row exist
    cur.execute(f"PRAGMA table_info({table})")
    existing_cols = {row[1] for row in cur.fetchall()}
    for col in data:
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")

    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    cur.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
        tuple(data.values()),
    )

    conn.commit()
    conn.close()


def send_to_server(table: str, **data) -> None:
    """Send a row of questionnaire data to the remote HTTP server.

    If the server cannot be reached, the data is stored locally in
    ``patient_responses.db`` instead of emitting repeated warnings.
    """
    if table == "conversation_history" and "patient_id" not in data:
        pid = os.environ.get("patient_id")
        if pid:
            data["patient_id"] = pid

    payload = json.dumps({"table": table, **data}).encode("utf-8")
    if SERVER_URL:
        req = request.Request(
            SERVER_URL, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            request.urlopen(req, timeout=5)
            return
        except Exception as exc:
            if os.environ.get("DEBUG_SERVER"):
                print(f"[WARN] Failed to send data to {SERVER_URL}: {exc}")

    _store_locally(table, data)
