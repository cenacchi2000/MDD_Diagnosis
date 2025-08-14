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

The host and port can also be provided via ``LIVE_LINK_HOST`` and
``LIVE_LINK_PORT`` environment variables which is useful when launching the
script via the Tritium IDE run button.


The bridge script (``ameca_livelink_bridge.py``) must be running on the
specified host and port. In Unreal, select subject ``AmecaBridge`` in the Live
Link panel for your MetaHuman avatar.
"""


import argparse
import json
import os

import logging
import socket
from typing import Dict, Iterable, List


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
mix_pose = None

# Demand prefixes to forward as generic facial channels. The MixDemandHub
# exposes a large set of values (brows, eyelids, nose, etc.) and the bridge
# only needs the raw numeric value.  Each demand name that begins with one of
# these prefixes will be forwarded to the Live Link bridge as an individual
# channel.
FACIAL_PREFIXES: tuple[str, ...] = (
    "Brow",
    "Eyelid",
    "Eye",
    "Gaze",
    "Nose",
    "Lip",
    "Mouth",
    "Jaw",
)



def _resolve_hosts(host: str) -> List[str]:
    """Return a list of destination IPs.

    ``host`` may be a comma separated list. If the token ``"auto"`` is present,
    the function expands it to include both the loopback address and the
    primary LAN address of the machine running the script. This helps when the
    exact Unreal Engine IP is unknown: one of the addresses will usually be
    correct.
    """

    logger.debug("Resolving host string %s", host)
    parts = [h.strip() for h in host.split(",") if h.strip()]
    ips: List[str] = []

    if "auto" in parts:
        parts.remove("auto")
        ips.append("127.0.0.1")
        try:
            hostname_ips = socket.gethostbyname_ex(socket.gethostname())[2]
            logger.debug("Discovered host IPs: %s", hostname_ips)
            for ip in hostname_ips:
                if ip not in ips:
                    ips.append(ip)
        except socket.gaierror as exc:
            logger.warning("Failed to resolve local host IPs: %s", exc)

    ips.extend(parts)
    logger.debug("Resolved hosts: %s", ips)
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

    global robot_state, head_yaw, head_pitch, head_roll, mix_pose

    if robot_state is None:
        try:
            logger.debug("Importing robot_state module")
            robot_state = system.import_library("../../../HB3/robot_state.py").state
            logger.debug("robot_state imported successfully")
        except Exception as exc:  # pragma: no cover - fails if run outside Tritium
            logger.exception("Failed to import robot_state")
            raise RuntimeError("robot_state unavailable; run inside Tritium") from exc


    if head_yaw is None:
        logger.debug("Acquiring head control interfaces")
        head_yaw = system.control("Head Yaw", "Mesmer Neck 1", acquire=["position"])
        head_pitch = system.control("Head Pitch", "Mesmer Neck 1", acquire=["position"])
        head_roll = system.control("Head Roll", "Mesmer Neck 1", acquire=["position"])

    if mix_pose is None:
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        logger.debug("Initial mix_pose hub: %s", mix_pose)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dests = [(h, port) for h in hosts]
    logger.info("Streaming to: %s", ", ".join(f"{h}:{port}" for h in hosts))
    if all(h.startswith("127.") for h in hosts):
        logger.warning(
            "Only streaming to loopback. If Unreal runs on another machine, supply its IP with --host"
        )


    mouth = system.unstable.owner.mouth_driver
    blink_state = False
    speech_state = False
    logger.debug("Initial mouth driver: %s", mouth)

    def send(payload: Dict[str, float | str]) -> None:
        data = json.dumps(payload).encode()
        for dest in dests:
            try:
                logger.debug("Sending %s to %s", payload, dest)
                sock.sendto(data, dest)
            except OSError as exc:
                logger.exception("Failed to send data to %s: %s", dest, exc)


    @system.tick(fps=60)
    def stream() -> None:
        nonlocal mouth, blink_state, speech_state
        global mix_pose
        if mouth is None:
            logger.debug("Mouth driver not set; attempting to reacquire")
            mouth = system.unstable.owner.mouth_driver
            logger.debug("Reacquired mouth driver: %s", mouth)
            if mouth is None:
                logger.debug("Mouth driver still unavailable; skipping tick")
                return

        head_vals: Dict[tuple[str, str], float] = {}
        current_mix = mix_pose or getattr(system.unstable.owner, "mix_pose", None)
        if current_mix is not None:
            if mix_pose is None:
                mix_pose = current_mix
                logger.debug("Reacquired mix_pose hub: %s", mix_pose)
            try:
                head_vals = current_mix.get_values()
                logger.debug(
                    "mix_pose head/neck values: %s",
                    {str(k): v for k, v in head_vals.items() if "Head" in k[0] or "Neck" in k[0]},
                )
            except Exception as exc:  # pragma: no cover - mix_pose may not be initialised
                logger.exception("Failed to read mix_pose values: %s", exc)

        yaw = head_vals.get(("Head Yaw", "Mesmer Neck 1"), head_yaw.position or 0.0)
        pitch = head_vals.get(("Head Pitch", "Mesmer Neck 1"), head_pitch.position or 0.0)
        pitch += head_vals.get(("Neck Pitch", "Mesmer Neck 1"), 0.0)
        roll = head_vals.get(("Head Roll", "Mesmer Neck 1"), head_roll.position or 0.0)
        roll += head_vals.get(("Neck Roll", "Mesmer Neck 1"), 0.0)

        pose_payload = {"type": "pose", "yaw": yaw, "pitch": pitch, "roll": roll}
        logger.debug("Pose payload: %s", pose_payload)
        send(pose_payload)

        # Forward all other MixDemandHub facial channels so the avatar can mirror
        # nose, brow, eyelid and gaze motion.  The demand name itself is sent as
        # the channel identifier; downstream consumers can remap as needed.
        for key, value in head_vals.items():
            try:
                demand = key[0]
            except Exception:
                logger.debug("Unexpected key format from mix_pose: %s", key)
                demand = str(key)
            if isinstance(demand, str) and any(
                demand.startswith(prefix) for prefix in FACIAL_PREFIXES
            ):
                send({"type": "blendshape", "name": demand, "value": float(value)})

        for name, weight in mouth.viseme_demands.items():
            logger.debug("Viseme %s weight %s", name, weight)
            if weight > 0.01:
                phoneme = VISEME_MAP.get(name)
                if phoneme:
                    send({"type": "viseme", "name": phoneme, "weight": float(weight)})

        open_amt = getattr(mouth, "mouth_open", 0.0)
        if callable(open_amt):  # ``mouth_open`` may be a @parameter partial
            try:
                open_amt = open_amt()
            except Exception as exc:
                logger.exception("Failed to read mouth_open: %s", exc)
                open_amt = 0.0

        logger.debug("Mouth open amount: %s", open_amt)
        if open_amt > 0.01:
            # Mouth driver exposes [0,2] range; Live Link expects [0,1]
            send({"type": "viseme", "name": "Open", "weight": float(open_amt) / 2.0})


        if robot_state.blinking and not blink_state:
            logger.debug("Blink detected")
            send({"type": "gesture", "name": "blink"})
        blink_state = robot_state.blinking
        logger.debug("Blink state: %s", blink_state)

        if robot_state.speaking != speech_state:
            send({"type": "speech", "speaking": bool(robot_state.speaking)})
            speech_state = robot_state.speaking

    if block:
        logger.debug("Blocking execution; entering runtime loop")
        run_fn = getattr(system, "run", None)
        if callable(run_fn):
            run_fn()
        else:  # pragma: no cover - real Tritium runtime drives the loop
            import time

            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                logger.debug("Interrupted by user")
                pass


class Activity:
    """Tritium activity entry point providing a run button in the IDE."""

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        # Allow environment variables to override defaults so users can select
        # the Unreal bridge destination without editing the script.
        env_host = os.environ.get("LIVE_LINK_HOST", "auto")
        env_port = int(os.environ.get("LIVE_LINK_PORT", "8210"))
        self.host = host or env_host
        self.port = port or env_port
        logger.debug("Activity created with host=%s port=%s", self.host, self.port)


    def on_start(self) -> None:
        logger.debug("Activity starting")
        run(_resolve_hosts(self.host), self.port, block=False)



def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Ameca facial data to Unreal Live Link")
    parser.add_argument(
        "--host",
        default=os.environ.get("LIVE_LINK_HOST", "127.0.0.1"),
        help=(
            "Destination IP of ameca_livelink_bridge. Accepts a comma-separated"
            " list. Use 'auto' to send to both loopback and the machine's LAN IP."
            " Can also be supplied via LIVE_LINK_HOST env var"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LIVE_LINK_PORT", "8210")),
        help="UDP port of the bridge (or LIVE_LINK_PORT env var)",
    )

    args = parser.parse_args()
    logger.debug("Parsed arguments: host=%s port=%s", args.host, args.port)
    run(_resolve_hosts(args.host), args.port)


if __name__ == "__main__":
    main()
