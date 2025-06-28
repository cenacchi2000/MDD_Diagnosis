"""
Restarts Pulseaudio audio daemon.

Audio interfaces such as the Behringer UMC202HD require a Pulseaudio restart if hot-plugging.
"""

import asyncio


class Activity:
    async def on_start(self):
        log.info("Stopping PulseAudio...")
        stop_process = await asyncio.create_subprocess_exec(
            "pulseaudio",
            "--kill",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await stop_process.communicate()

        if stop_process.returncode == 0:
            log.info("PulseAudio stopped successfully")
        else:
            log.error(f"Error stopping PulseAudio: {stderr.decode().strip()}")

        await asyncio.sleep(1)

        log.info("Starting PulseAudio...")
        start_process = await asyncio.create_subprocess_exec(
            "pulseaudio",
            "--start",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await start_process.communicate()

        if start_process.returncode == 0:
            log.info("PulseAudio started successfully")
        else:
            log.error(f"Error starting PulseAudio: {stderr.decode().strip()}")
        self.stop()