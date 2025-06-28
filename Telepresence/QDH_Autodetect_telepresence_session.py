"""
QDH Detect whether a TP session is active based on the existance of a PulseAudio sink-input
"""

import asyncio


class Activity:
    @system.tick(fps=1)
    async def on_tick(self):
        process = await asyncio.create_subprocess_exec(
            "pactl",
            "list",
            "sink-inputs",
            env={"PULSE_RUNTIME_PATH": "/tmp/pulseaudio"},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()
        if process.returncode != 0:
            print("pactl failed!" + process.stderr)
        output = " "
        session_active = False
        while output and not session_active:
            output = await process.stdout.read(4089)
            session_active = b'application.name = "tritium_gateway"' in output
        probe("telepresence_session_active", session_active)
        system.messaging.post(
            "telepresence", {"type": "session_active", "value": session_active}
        )
