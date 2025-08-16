"""Drive an Ameca robot from human pose via Unreal MetaHuman.

This example captures a live video stream, extracts a body pose with MediaPipe,
streams the pose to an Unreal Engine MetaHuman over UDP, and forwards a reduced
set of joint angles to an Ameca robot using a simple Tritium-compatible JSON
packet.  The packet format is intentionally minimal and should be adapted to
your robot's control stack.

Usage:
    python avatar_to_ameca.py --unreal 127.0.0.1:9999 --ameca 192.168.1.50:9000

Press ``q`` in the preview window to quit.
"""

from __future__ import annotations

import argparse
import json
import math
import socket
from typing import Dict, Tuple

import cv2
import mediapipe as mp


# ---------------------------------------------------------------------------
# Pose utilities
# ---------------------------------------------------------------------------

mp_pose = mp.solutions.pose


def _angle(a: Tuple[float, float, float],
           b: Tuple[float, float, float],
           c: Tuple[float, float, float]) -> float:
    """Return the angle at point ``b`` formed by ``a-b-c`` in degrees."""
    v1 = (a[0] - b[0], a[1] - b[1], a[2] - b[2])
    v2 = (c[0] - b[0], c[1] - b[1], c[2] - b[2])
    v1_mag = math.sqrt(sum(i * i for i in v1))
    v2_mag = math.sqrt(sum(i * i for i in v2))
    if v1_mag == 0 or v2_mag == 0:
        return 0.0
    dot = sum(v1[i] * v2[i] for i in range(3)) / (v1_mag * v2_mag)
    dot = max(min(dot, 1.0), -1.0)
    return math.degrees(math.acos(dot))


def compute_joint_angles(landmarks: mp.framework.formats.landmark_pb2.LandmarkList) -> Dict[str, float]:
    """Extract a few example joint angles from MediaPipe pose landmarks."""
    lm = landmarks.landmark
    left = _angle(
        (lm[11].x, lm[11].y, lm[11].z),
        (lm[13].x, lm[13].y, lm[13].z),
        (lm[15].x, lm[15].y, lm[15].z),
    )
    right = _angle(
        (lm[12].x, lm[12].y, lm[12].z),
        (lm[14].x, lm[14].y, lm[14].z),
        (lm[16].x, lm[16].y, lm[16].z),
    )
    return {"L_Elbow": left, "R_Elbow": right}


# ---------------------------------------------------------------------------
# Networking helpers
# ---------------------------------------------------------------------------

def parse_host_port(spec: str) -> Tuple[str, int]:
    host, port = spec.split(":")
    return host, int(port)


def send_to_unreal(sock: socket.socket, addr: Tuple[str, int], landmarks) -> None:
    data = [(lm.x, lm.y, lm.z) for lm in landmarks.landmark]
    payload = json.dumps({"landmarks": data}).encode()
    sock.sendto(payload, addr)


def send_to_ameca(sock: socket.socket, addr: Tuple[str, int], angles: Dict[str, float]) -> None:
    """Send joint angles to Ameca.

    In a real deployment ``build_tritium_packet`` should be replaced with the
    robot's binary protocol.  Here we simply encode the angles as JSON.
    """
    payload = json.dumps({"angles": angles}).encode()
    sock.sendto(payload, addr)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unreal", default="127.0.0.1:9999",
                        help="<host:port> of Unreal UDP listener")
    parser.add_argument("--ameca", default="127.0.0.1:9000",
                        help="<host:port> for Ameca Tritium bridge")
    args = parser.parse_args()

    unreal_addr = parse_host_port(args.unreal)
    ameca_addr = parse_host_port(args.ameca)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pose = mp_pose.Pose()
    cap = cv2.VideoCapture(0)

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            if results.pose_landmarks:
                send_to_unreal(sock, unreal_addr, results.pose_landmarks)
                angles = compute_joint_angles(results.pose_landmarks)
                send_to_ameca(sock, ameca_addr, angles)
            cv2.imshow("Pose", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        pose.close()
        sock.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
