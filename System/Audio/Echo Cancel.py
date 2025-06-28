"""
This script enables software echo cancellation on an external microphone.

Requirements:
* `sudo apt install pulseaudio-module-echo-cancel` might be required on some versions of Tritium OS

Usage:
* Start this script
* On the audio page:
** Set default source to VIRTUAL_SOURCE_NAME
** Set default sink to VIRTUAL_SINK_NAME

Settings:
* SOURCE_TO_PROCESS: This is the pulseaudio name of the mic you want to remove echos from
* SINK_TO_OUTPUT_TO: This is the pulseaudio name of the sink you want to output to

This script loads a pulseaudio module which in turn creates these virtual pulseaudio devices:
* A Source called VIRTUAL_SOURCE_NAME which is the processed version of SOURCE_TO_PROCESS
* A Sink called VIRTUAL_SINK_NAME which forwards audio to the AEC algorithm and SINK_TO_OUTPUT_TO
"""

import asyncio
import fnmatch
import subprocess

# Do not set this source to be the XMOS - general rule of thumb is:
#   When using the XMOS mic, let it do the echo cancellation (might need "Combine Audio Sinks.py")
#   When using an external mic, use this script for echo cancellation.
# Globs are supported for lookups
SOURCE_TO_PROCESS = (
    "alsa_input.usb-R__DE_Microphones_R__DE_VideoMic_NTG_*.analog-stereo"
)
SINK_TO_OUTPUT_TO = "alsa_output.usb-XMOS_XMOS_VocalFusion_St__UAC1.0_-00.analog-stereo"

VIRTUAL_SOURCE_NAME = "External-Mic-No-Echo"
VIRTUAL_SINK_NAME = "Echo-Cancel-External-Mic"

assert len(SOURCE_TO_PROCESS.split()) == 1, "No spaces allowed"
assert len(SINK_TO_OUTPUT_TO.split()) == 1, "No spaces allowed"
assert len(VIRTUAL_SOURCE_NAME.split()) == 1, "No spaces allowed"
assert len(VIRTUAL_SINK_NAME.split()) == 1, "No spaces allowed"


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
        log.error(f"pactl failed!: \n{await process.stderr.read(4096)}")
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
    def on_stop(self):
        subprocess.run(
            ["pactl", "unload-module", "module-echo-cancel"],
            env={"PULSE_RUNTIME_PATH": "/tmp/pulseaudio"},
        )

    # We repeatedly re-run this so that as devices are connected/remove
    # or if pulse crashes we re-instantiate the desired module.
    @system.tick(fps=1)
    async def on_tick(self):
        # Discover what devices are connected
        sources = await pactl_list("sources")

        if not sources:
            probe("status", "SOURCES LIST FAILED")
            return

        # Check if this echo cancellation module is loaded
        echo_cancel_src_row = filter_column_glob(
            sources,
            2,
            "module-echo-cancel.c",
        )
        if echo_cancel_src_row:
            probe("status", "ALREADY EXISTS")
            return

        # Check if the requested source is present
        source_row = filter_column_glob(
            sources,
            1,
            SOURCE_TO_PROCESS,
        )
        if not source_row:
            probe("status", "SOURCE NOT FOUND")
            return

        # Discover what devices are connected
        sinks = await pactl_list("sinks")
        if not sinks:
            probe("status", "SINKS LIST FAILED")
            return

        # Check if the requested sink is present
        sink_row = filter_column_glob(
            sinks,
            1,
            SINK_TO_OUTPUT_TO,
        )
        if not sink_row:
            probe("status", "SINK NOT FOUND")
            return

        # Load the echo cancellation module now that we have the right args
        process = await run_subprocess(
            "pactl",
            "load-module",
            "module-echo-cancel",
            " ".join(
                [
                    f"source_name={VIRTUAL_SOURCE_NAME}",
                    f"source_master={source_row[0][1]}",
                    f"sink_master={sink_row[0][1]}",
                    f"sink_name={VIRTUAL_SINK_NAME}",
                    "use_master_format=1",
                    "aec_method=webrtc",
                    'aec_args="analog_gain_control=0 digital_gain_control=0"',
                ]
            ),
        )
        if not process:
            probe("status", "ERROR LOADING MODULE")
        else:
            probe("status", "ADDED")