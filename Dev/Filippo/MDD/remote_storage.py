import os
import requests

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000/store")


def send_to_server(table: str, **data) -> None:
    """Send a row of questionnaire data to the remote HTTP server."""
    payload = {"table": table, **data}
    try:
        requests.post(SERVER_URL, json=payload, timeout=5)
    except Exception as exc:
        print(f"[WARN] Failed to send data to {SERVER_URL}: {exc}")
