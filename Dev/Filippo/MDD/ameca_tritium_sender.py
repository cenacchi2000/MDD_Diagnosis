"""Send Ameca viseme and head pose data to Unreal Live Link.

This module runs inside the Tritium environment and forwards mouth viseme
weights, head orientation and blink events to the Live Link bridge running on
an Unreal Engine machine.

Usage:
    python ameca_tritium_sender.py --host 127.0.0.1 --port 8210

The bridge script (``ameca_livelink_bridge.py``) must be running on the
specified host and port. In Unreal, select subject ``AmecaBridge`` in the Live
Link panel for your MetaHuman avatar.
"""

import argparse
import json
import socket
from typing import Dict

# Map Tritium viseme names to Live Link phoneme identifiers
VISEME_MAP = {
    "Viseme A": "AA",
    "Viseme CH": "CH",
    "Viseme Closed": "M",
    "Viseme E": "EH",
    "Viseme F": "F",
    "Viseme I": "IY",
    "Viseme ING": "NG",
    "Viseme KK": "K",
    "Viseme M": "M",
    "Viseme NN": "N",
    "Viseme O": "OW",
    "Viseme RR": "ER",
    "Viseme SS": "S",
    "Viseme U": "UW",
}

# Access robot state for blink detection
robot_state = system.import_library("../../../HB3/robot_state.py").state

# Head control handles
head_yaw = system.control("Head Yaw", "Mesmer Neck 1", acquire=["position"])
head_pitch = system.control("Head Pitch", "Mesmer Neck 1", acquire=["position"])
head_roll = system.control("Head Roll", "Mesmer Neck 1", acquire=["position"])


def run(host: str, port: int) -> None:
    """Start streaming head pose and viseme data to the bridge."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (host, port)
    mouth = system.unstable.owner.mouth_driver
    blink_state = False

    def send(payload: Dict[str, float | str]) -> None:
        sock.sendto(json.dumps(payload).encode(), dest)

    @system.tick(fps=60)
    def stream() -> None:
        nonlocal mouth, blink_state
        if mouth is None:
            mouth = system.unstable.owner.mouth_driver
            if mouth is None:
                return

        send(
            {
                "type": "pose",
                "yaw": head_yaw.position or 0.0,
                "pitch": head_pitch.position or 0.0,
                "roll": head_roll.position or 0.0,
            }
        )

        for name, weight in mouth.viseme_demands.items():
            if weight > 0.01:
                phoneme = VISEME_MAP.get(name)
                if phoneme:
                    send({"type": "viseme", "name": phoneme, "weight": float(weight)})

        if robot_state.blinking and not blink_state:
            send({"type": "gesture", "name": "blink"})
        blink_state = robot_state.blinking

    system.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Ameca facial data to Unreal Live Link")
    parser.add_argument("--host", default="127.0.0.1", help="IP address of ameca_livelink_bridge")
    parser.add_argument("--port", type=int, default=8210, help="UDP port of the bridge")
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
