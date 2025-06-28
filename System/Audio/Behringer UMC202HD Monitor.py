"""
This script monitors the Behringer UMC202HD and deals with a quirk where it occasionally does not initialize properly.
When this happens, it resets the card profile to properly initialize the sources and sinks.
"""

import asyncio
import fnmatch

BEHRINGER_CARD_NAME = "*UMC202HD*"


async def run_subprocess(*args):
    process = await asyncio.create_subprocess_exec(
        *args,
        env={"PULSE_RUNTIME_PATH": "/tmp/pulseaudio"},
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    await process.wait()
    if process.returncode != 0:
        log.warning("pactl failed!", await process.stderr.read(4096))
        return None
    return process


async def pactl_list(*args):
    subprocess = await run_subprocess("pactl", "list", "short", *args)
    if subprocess is None:
        return None
    ret = await subprocess.stdout.read()
    return [tuple(line.split("\t")) for line in ret.decode().split("\n") if line]


def filter_column_glob(lines: list[str], column_idx: int, matcher: str):
    filtered_lines = []
    for line in lines:
        if fnmatch.fnmatchcase(line[column_idx], matcher):
            filtered_lines.append(line)
    return filtered_lines


class Activity:
    def __init__(self):
        self.card_id = None
        self.initialized = False  # Used to log initial status only once

    async def find_card_id(self):
        # Get list of cards
        cards = await pactl_list("cards")
        if not cards:
            probe("status", "CARDS LIST FAILED")
            log.warning("Failed to get cards list")
            self.card_id = None
            return False

        # Find Behringer card
        behringer_card = filter_column_glob(cards, 1, BEHRINGER_CARD_NAME)
        if not behringer_card:
            probe("status", "CARD NOT FOUND")
            log.warning("Behringer card not found")
            self.card_id = None
            return False

        self.card_id = behringer_card[0][0]
        return True

    @system.tick(fps=0.5)
    async def on_tick(self):
        # If we don't have a card_id, try to find it
        if self.card_id is None:
            if not await self.find_card_id():
                probe("status", "CARD NOT FOUND")
                if not self.initialized:
                    log.warning("Behringer card not found")
                    self.initialized = True
                return

        # Check if sources and sinks exist
        sources = await pactl_list("sources")
        sinks = await pactl_list("sinks")
        if not sources or not sinks:
            probe("status", "AUDIO LIST FAILED")
            log.warning("Failed to get sources or sinks list")
            self.card_id = None  # Reset card_id to force recheck next time
            return

        behringer_sources = filter_column_glob(sources, 1, BEHRINGER_CARD_NAME)
        behringer_sinks = filter_column_glob(sinks, 1, BEHRINGER_CARD_NAME)

        # If we see the card but no sources or sinks, we need to reset the profile
        if not behringer_sources or not behringer_sinks:
            # check that the card is still there
            if not await self.find_card_id():
                probe("status", "CARD NOT FOUND")
                log.warning("Behringer card disconnected")
                self.card_id = None
                return

            log.warning(
                "Behringer sources/sinks not found even though card is present, resetting profile"
            )
            # Turn profile off and back on
            await run_subprocess("pactl", "set-card-profile", self.card_id, "off")
            await asyncio.sleep(1)
            await run_subprocess(
                "pactl", "set-card-profile", self.card_id, "input:stereo+output:stereo"
            )
            probe("status", "REINITIALIZED")
        else:
            probe("status", "OK")