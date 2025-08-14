"""Send Ameca viseme and head pose data to Unreal Live Link.

This module runs inside the Tritium environment and forwards mouth viseme
weights, **mouth openness**, head orientation and blink events to the Live Link
bridge running on an Unreal Engine machine. When loaded as a Tritium
``Activity`` it exposes a run button in the IDE; it can also be launched as a
standalone script. Ensure the standard Ameca control stack (e.g. ``Chat_Controller.py``
and ``HB3_Controller.py``) is running so that head pose, blinking and visemes
are populated by the robot.

Usage examples::

    # Stream to the bridge on a specific machine
    python ameca_tritium_sender.py --host 10.63.3.105 --port 8210

    # Try both loopback and the host's LAN address
    python ameca_tritium_sender.py --host auto

The bridge script (``ameca_livelink_bridge.py``) must be running on the
specified host and port. In Unreal, select subject ``AmecaBridge`` in the Live
Link panel for your MetaHuman avatar.
"""


import argparse
import json
import socket
from typing import Dict, Iterable, List

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

robot_state = None
head_yaw = head_pitch = head_roll = None


def _resolve_hosts(host: str) -> List[str]:
    """Return a list of destination IPs.

    ``host`` may be a comma separated list. If the token ``"auto"`` is present,
    the function expands it to include both the loopback address and the
    primary LAN address of the machine running the script. This helps when the
    exact Unreal Engine IP is unknown: one of the addresses will usually be
    correct.
    """

    parts = [h.strip() for h in host.split(",") if h.strip()]
    ips: List[str] = []

    if "auto" in parts:
        parts.remove("auto")
        ips.append("127.0.0.1")
        try:
            hostname_ips = socket.gethostbyname_ex(socket.gethostname())[2]
            for ip in hostname_ips:
                if ip not in ips:
                    ips.append(ip)
        except socket.gaierror:
            pass

    ips.extend(parts)
    return ips


def run(hosts: Iterable[str], port: int, *, block: bool = True) -> None:
    """Start streaming head pose and viseme data to the bridge.

    Parameters
    ----------
    hosts:
        Iterable of destination IP addresses for the Unreal bridge.
    port:
        UDP port on which the bridge is listening.
    block:
        When ``True`` the function will block the current thread after
        registering the tick callback. This is useful when executing the
        module as a standalone script. Tritium's activity runtime supplies
        its own loop, so ``Activity.on_start`` sets ``block=False`` to avoid
        hanging the IDE.
    """
    global robot_state, head_yaw, head_pitch, head_roll

    if robot_state is None:
        try:
            robot_state = system.import_library("../../../HB3/robot_state.py").state
        except Exception as exc:  # pragma: no cover - fails if run outside Tritium
            raise RuntimeError("robot_state unavailable; run inside Tritium") from exc

    if head_yaw is None:
        head_yaw = system.control("Head Yaw", "Mesmer Neck 1", acquire=["position"])
        head_pitch = system.control("Head Pitch", "Mesmer Neck 1", acquire=["position"])
        head_roll = system.control("Head Roll", "Mesmer Neck 1", acquire=["position"])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dests = [(h, port) for h in hosts]
    print("Streaming to:", ", ".join(f"{h}:{port}" for h in hosts))

    mouth = system.unstable.owner.mouth_driver
    blink_state = False

    def send(payload: Dict[str, float | str]) -> None:
        data = json.dumps(payload).encode()
        for dest in dests:
            sock.sendto(data, dest)

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

        open_amt = getattr(mouth, "mouth_open", 0.0)
        if open_amt > 0.01:
            # Mouth driver exposes [0,2] range; Live Link expects [0,1]
            send({"type": "viseme", "name": "Open", "weight": float(open_amt) / 2.0})

        if robot_state.blinking and not blink_state:
            send({"type": "gesture", "name": "blink"})
        blink_state = robot_state.blinking

    if block:
        run_fn = getattr(system, "run", None)
        if callable(run_fn):
            run_fn()
        else:  # pragma: no cover - real Tritium runtime drives the loop
            import time

            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                pass


class Activity:
    """Tritium activity entry point providing a run button in the IDE."""

    def __init__(self, host: str = "auto", port: int = 8210) -> None:
        self.host = host
        self.port = port

    def on_start(self) -> None:
        run(_resolve_hosts(self.host), self.port, block=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Ameca facial data to Unreal Live Link")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Destination IP of ameca_livelink_bridge. Accepts a comma-separated"
            " list. Use 'auto' to send to both loopback and the machine's LAN IP"
        ),
    )
    parser.add_argument("--port", type=int, default=8210, help="UDP port of the bridge")
    args = parser.parse_args()
    run(_resolve_hosts(args.host), args.port)


if __name__ == "__main__":
    main()
