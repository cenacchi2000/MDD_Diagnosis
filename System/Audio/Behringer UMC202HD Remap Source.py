"""
Creates a remapped pulseaudio source which only grabs the left channel (Input 1) from a Behringer UMC202HD

This uses pulseaudio's module-remap-source
See: https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/#module-remap-source

Pulseaudio is the audio daemon used on most ubuntu distributions.
* "sinks" are audio output devices.
* "sources" are audio input devices.
* "sink-inputs" are audio streams playing from applications into sinks.
* "source-outputs" are audio streams recording from sources into applications.
* "module-remap-source" creates a virtual source and a "source-output" for
  the source being listened to which redirects the filtered/remapped data into
  the source-outputs for the new virtual source.

You can use very similar logic to create a module-remap-sink to output to (a) specific
channel(s) of a sink - and even to send seperate streams to different sinks.
"""

import asyncio
import fnmatch

MASTER_SOURCE = "alsa_input.usb-BEHRINGER_UMC202HD_192k_12345678-00.analog-input-stereo"
REMAPPED_SOURCE = "Behringer_Mono_Left"


# We use "pactl" which is a commandline client for pulseaudio to inspect and change
# audio device configuration.
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
    # Split by newline and tab, into a list of tuples
    return [tuple(line.split("\t")) for line in ret.decode().split("\n") if line]


def filter_column_glob(lines: list[str], column_idx: int, matcher: str):
    filtered_lines = []
    for line in lines:
        if fnmatch.fnmatchcase(line[column_idx], matcher):
            filtered_lines.append(line)
    return filtered_lines


class Activity:
    @system.tick(fps=0.5)
    async def on_tick(self):
        # Discover what devices are connected
        sources = await pactl_list("sources")

        if not sources:
            probe("status", "SOURCES LIST FAILED")
            return

        # Check if the remapped source exists
        remapped_src_row = filter_column_glob(sources, 1, REMAPPED_SOURCE)
        if remapped_src_row:
            probe("status", "ALREADY EXISTS")
            return

        # Check if the master source exists
        master_src_row = filter_column_glob(sources, 1, MASTER_SOURCE)
        if not master_src_row:
            probe("status", "SOURCE NOT FOUND")
            return
        # Load the remap module
        process = await run_subprocess(
            "pactl",
            "load-module",
            "module-remap-source",
            " ".join(
                [
                    f"master={MASTER_SOURCE}",
                    "master_channel_map=front-left",
                    "channel_map=mono",
                    f"source_name={REMAPPED_SOURCE}",
                    "channels=1",  # This should be implied, but including for completeness
                    "remix=false",  # THIS MUST BE SET, pulseaudio has a crazy default of merging other channels
                    "rate=44100",  # For some reason when using remix=false, we have to specify the rate manually
                    "format=s32le",  # This should be implied, but including for completeness
                ]
            ),
        )
        if not process:
            probe("status", "ERROR")
        else:
            probe("status", "ADDED")