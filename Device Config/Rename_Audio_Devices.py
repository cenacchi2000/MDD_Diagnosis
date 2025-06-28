"""
Renames audio devices to be more human readable

e.g. 
"alsa_input.usb-www.engineeredarts.co.uk_Mesmer_Stereo_Microphone_v0.1.5_376633543033-00.analog-stereo" 
-> "Ear Mics"

Will take effect once the Audio Device Host node has been restarted
"""


def get_human_readable_name(device_class_name):
    match device_class_name:
        case (
            "XMOS-Mono"
            | "alsa_input.usb-XMOS_XVF3800_Voice_Processor_000000-00.analog-stereo"
        ):
            return "Front Mic"

        case "alsa_input.usb-XMOS_XMOS_VocalFusion_St__UAC1.0_-00.multichannel-input":
            return "Front Mic Raw"

        case (
            "alsa_output.usb-XMOS_XMOS_VocalFusion_St__UAC1.0_-00.analog-stereo"
            | "alsa_output.usb-XMOS_XVF3800_Voice_Processor_000000-00.analog-stereo"
        ):
            return "Chest Speaker"

    # Ear Mics can differ by version so we can't do a direct match
    if device_class_name.startswith(
        "alsa_input.usb-www.engineeredarts.co.uk_Mesmer_Stereo_Microphone_"
    ):
        return "Ear Mics"


class Activity:
    async def on_start(self):
        for device in system.unstable.owner.device_manager.devices:
            if device.identifier.startswith("audio_device_host_") and device.online:
                if new_name := get_human_readable_name(device.device_class.name):
                    if device.logical_name == new_name:
                        # device already has human readable name
                        continue

                    idx = 0
                    for d in await system.unstable.stash.get(
                        "/profile/nodes/audio_device_host/devices"
                    ):
                        if type(d) is dict and "key" in d and d["key"] == device.serial:
                            break
                        idx += 1
                    else:
                        # no config exists for this device, so we define the key for the new entry
                        await system.unstable.stash.set(
                            f"/profile/nodes/audio_device_host/devices/{idx}/key",
                            device.serial,
                        )

                    log.info(f'renaming "{device.logical_name}" to "{new_name}"')
                    await system.unstable.stash.set(
                        f"/profile/nodes/audio_device_host/devices/{idx}/value/name",
                        new_name,
                    )
        self.stop()