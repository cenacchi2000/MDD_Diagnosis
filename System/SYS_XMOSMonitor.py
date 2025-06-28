########### Essential control function - DO NOT DELETE ###########
# This system script monitors XMOS device and toggles USB power or speaker Vmot / Vcon to attempt to fix any problems
# Version 1.1.2
# Updates:
#     0.0.1: Function created by combining the previous XMOS Port Cycle.py and SYS_ToggleXMOS.py,
#            as well as modifying it so it monitors Vcon and Vmot continuously.
#     1.0.0: Fix startup race condition.
#     1.0.1: Make resilient to instantaneous start & restart
#     1.0.2: Add USB path for batch 6 robots
#     1.1.0: Switch to using controls instead of parameters
#     1.1.1: Check for disconnections properly with audio device host
#            as XVF3800 host device stays online even if mic is unplugged
#     1.1.2: Increase wait time for XMOS to enumerate after usb is powered on.
#            Turn on usb if script was stopped while usb was powered off
#     1.1.3: Only check original pulse names when looking for disconnections from the audio device host

import asyncio
from asyncio import sleep

speaker_control = system.control(
    "Speaker Power",
    None,
    acquire=["vmotor_voltage", "vcontrol_voltage"],
    required=False,
)

XMOS_VOLTAGE_THRESHOLD = 19  # Volts

CONFIG = system.import_library("../Config/HB3.py").CONFIG

# Requires /etc/sudoers.d/xmos_disable
contents = """
tritium ALL=(root) NOPASSWD: /usr/sbin/uhubctl
"""

EXPECTED_USB_DESCRIPTIONS = [
    "XMOS VocalFusion St (UAC1.0)",
    "XVF3800 Voice Processor",
]

# Names of xmos mic devices provided by audio host device, using the original unmapped name
# to avoid a dependency on the correct renaming of devices.
EXPECTED_AUDIO_HOST_MIC_DEVICES = [
    "alsa_input.usb-XMOS_XVF3800_Voice_Processor_000000-00.analog-stereo",
    "alsa_input.usb-XMOS_XMOS_VocalFusion_St__UAC1.0_-00.multichannel-input",
]

# Name of the device provided by xmos device host.
EXPECTED_DEVICE_NAMES = ["Xmos Linear Mic Array", "XMOS XVF3800"]

EXPECTED_USB_PATHS = [
    "3-1.1",  # ac-0040 & batch 6
    "3-5.2",  # ac-0004, ac-0014, ac-0015
    "3-6.6.4",  # ac-0010
    "3-5.3",  # ac-0017
    "3-6.2",  # ac-0016
    "3-6.7",  # ac-0006
    "1-4.2",  # ad-0003
    "3-1.3",  # ad-0008, az-0001
    "3-7.3",  # ay-0009
]

USB_POWER_OFF_WAIT = 2  # Seconds to wait after powering off USB
USB_POWER_ON_WAIT = 15  # Seconds to wait after powering on USB


async def run_subprocess(*args):
    process = await asyncio.create_subprocess_exec(
        *args,
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    await process.wait()
    if process.returncode != 0:
        print("command failed!", await process.stderr.read(4096))
        return None
    return process


async def control_usb_power(path, port, power_on=True):
    """Control USB port power using uhubctl.

    Args:
        path (str): USB hub path
        port (str): Port number
        power_on (bool): True to power on, False to power off
    """
    action = "on" if power_on else "off"
    args = ["sudo", "/usr/sbin/uhubctl", "-a", action, "-l", path, "-p", port]
    if not power_on:
        # Multiple repeats for turning off. According to uhubctl docs it is needed for some devices only for turning off.
        args.extend(["-r", "12"])
    return await run_subprocess(*args)


class Activity:
    usb_path = None

    async def on_start(self):

        self.initialized = False
        # used to check for disconnections
        self.audio_host_mic_device_identifier = None

        if CONFIG["ROBOT_TYPE"] == CONFIG["ROBOT_TYPES"].AMECA_DESKTOP:
            # monitoring vcon and vmot not required for desktop robots
            return

        # Allow time for the parameters to be acquired
        await sleep(0.5)

        # Acquire the xmos power parameters
        while (
            speaker_control.vmotor_voltage is None
            or speaker_control.vcontrol_voltage is None
        ):
            log.warning(
                "Speaker Power properties are not available. Power Distribution Board might be offline. Retrying in 10 seconds..."
            )
            probe("PWR_STATUS", "Speaker Power properties not available")
            await sleep(10)

        # Monitor the xmos power parameters
        while True:
            await self.monitor_power()
            await sleep(5)

    async def find_xmos_usb_path(self):
        for d in EXPECTED_USB_PATHS:
            try:
                name = open(f"/sys/bus/usb/devices/{d}/product").read()
            except FileNotFoundError:
                name = ""
            if name.strip() in EXPECTED_USB_DESCRIPTIONS:
                return d
            await sleep(0.05)

    def find_xmos_tritium_device(self):
        for d in system.unstable.owner.device_manager.devices:
            if d.logical_name in EXPECTED_DEVICE_NAMES:
                return d

    def find_audio_input_tritium_device(self):
        """
        Return the mic device provided by audio device host.
        We can use it to check for disconnections regardless of having a working device host for that specific xmos.

        Originally switched from using the xmos device host when we started working on XVF3800.
        """
        host = system.unstable.owner.device_manager.get_device_host("audio_device_host")
        for device in host.devices:
            if device.device_class.name in EXPECTED_AUDIO_HOST_MIC_DEVICES:
                return device

    async def monitor_power(self):
        vcon = speaker_control.vcontrol_voltage
        vmot = speaker_control.vmotor_voltage

        if vcon is None or vmot is None:
            probe("PWR_STATUS", "Parameters not available")
            return

        vcon_good = vcon > XMOS_VOLTAGE_THRESHOLD
        vmot_good = vmot > XMOS_VOLTAGE_THRESHOLD

        if vcon_good and vmot_good:
            probe("PWR_STATUS", "OK")
            return

        bad_voltages = []

        if not vcon_good:
            bad_voltages.append("Vcon")
            speaker_control.vcontrol_enable = False
        if not vmot_good:
            bad_voltages.append("Vmot")
            speaker_control.vmotor_enable = False

        probe("PWR_STATUS", "POWERING OFF " + ", ".join(bad_voltages))

        await sleep(2)

        if not vcon_good:
            speaker_control.vcontrol_enable = True
        if not vmot_good:
            speaker_control.vmotor_enable = True
        probe("PWR_STATUS", "POWERING ON " + ", ".join(bad_voltages))

    async def initialize_xmos(self, xmos_device_logical_name):
        """
        Does any initialization required on first connection
        """
        if xmos_device_logical_name == "XMOS XVF3800":
            # Need to manually set volume for 3800
            await run_subprocess("amixer", "-c", "Processor", "sset", "PCM,1", "100")

    @system.tick(fps=0.1)
    async def monitor_usb(self):
        d = self.find_xmos_tritium_device()
        if d and d.online:
            need_to_toggle_usb = False
            # Xmos device online - for XVF3800 it does not mean that it is connected, just that xmos device host script is running
            # We will use audio device host mic device to check for disconnections
            audio_device = self.find_audio_input_tritium_device()
            if audio_device and audio_device.online:
                if audio_device.identifier != self.audio_host_mic_device_identifier:
                    # Potential reconnection, might need to re-initialize
                    self.initialized = False
                    self.audio_host_mic_device_identifier = audio_device.identifier
                    probe("AUDIO_STATUS", "UNINITIALIZED")
                else:
                    probe("AUDIO_STATUS", "OK")
            else:
                # Audio device not online, usb might be erroring / disconnected. Toggle usb if erroring
                need_to_toggle_usb = True
                log.warning(
                    "XMOS Audio device not online, usb might be erroring / disconnected. Will attempt to toggle usb if it is erroring"
                )
                probe("AUDIO_STATUS", "MISSING")

            if not need_to_toggle_usb:
                probe("USB_STATUS", "OK")

                if not self.initialized:
                    await self.initialize_xmos(d.logical_name)
                    self.initialized = True
                return

        if not self.usb_path:
            self.usb_path = await self.find_xmos_usb_path()
        if self.usb_path is None:
            probe("USB_STATUS", "NO USB DEVICE")
            return

        probe("USB_STATUS", "POWERING OFF")
        path, port = self.usb_path.rsplit(".", 1)
        await control_usb_power(path, port, power_on=False)

        await sleep(USB_POWER_OFF_WAIT)

        probe("USB_STATUS", "POWERING ON")
        await control_usb_power(path, port, power_on=True)

        await sleep(USB_POWER_ON_WAIT)

    def on_stop(self):
        # Turn on usb in case script was stopped while usb was powered off
        if self.usb_path:
            path, port = self.usb_path.rsplit(".", 1)
            asyncio.create_task(control_usb_power(path, port, power_on=True))