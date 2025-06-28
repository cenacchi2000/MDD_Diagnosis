import os
import json
from urllib import request

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:5000/store")


def send_to_server(table: str, **data) -> None:
    """Send a row of questionnaire data to the remote HTTP server."""
    payload = json.dumps({"table": table, **data}).encode("utf-8")
    req = request.Request(
        SERVER_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        request.urlopen(req, timeout=5)
    except Exception as exc:
        print(f"[WARN] Failed to send data to {SERVER_URL}: {exc}")
