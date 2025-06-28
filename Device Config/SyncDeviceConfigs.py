"""
Add a short description of your script here

See https://tritiumrobot.cloud/docs/ for more information
"""

import os
import re

dcc_manager_lib = system.import_library("./Lib/DeviceConfigCloudManager.py")
compare_configs_lib = system.import_library("./Lib/CompareConfigs.py")
stash = system.unstable.stash


class Activity:
    def on_start(self):
        self.dcc_manager = dcc_manager_lib.DeviceConfigCloudManager()
        self.compare_configs = compare_configs_lib.CompareConfigs()
        pass

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    async def get_device_customization_idx(self, serial):
        profile_devices = await system.unstable.stash.get(
            "/profile/nodes/proxy_device_host_usb/devices"
        )
        idx = 0
        for d in profile_devices:
            if type(d) is dict and "key" in d and d["key"] == serial:
                return idx
            idx += 1
        return len(profile_devices)

    async def get_device_state_idx(self, serial):
        profile_device_states = await system.unstable.stash.get(
            "/profile/nodes/proxy_device_host_usb/device_states"
        )
        idx = 0
        for ds in profile_device_states:
            if type(ds) is dict and "key" in ds and ds["key"] == serial:
                return idx
            idx += 1

        return len(profile_device_states)

    """Configure a device in stash
    @param: tritium_serial The serial of the device which should be configured ex.: USB BDC 1234567890AB
    @param: config The confiuration object {'device_states': ... 'device_customization': ...}
    @param: tritium_rename_serial If this parameter is set it will try to overwrite the config of an already existing serial
    """

    async def configure_device_from_config(
        self, tritium_serial, config, tritium_serial_to_be_overwritten=None
    ):
        device_customization_idx = await self.get_device_customization_idx(
            tritium_serial
        )
        device_state_idx = await self.get_device_state_idx(tritium_serial)

        if tritium_serial_to_be_overwritten is not None:
            device_customization_idx = await self.get_device_customization_idx(
                tritium_serial_to_be_overwritten
            )
            device_state_idx = await self.get_device_state_idx(
                tritium_serial_to_be_overwritten
            )
        # set serial
        await system.unstable.stash.set(
            f"/profile/nodes/proxy_device_host_usb/devices/{device_customization_idx}/key",
            tritium_serial,
        )

        # set data
        await system.unstable.stash.set(
            f"/profile/nodes/proxy_device_host_usb/devices/{device_customization_idx}/value",
            config["device_customization"],
        )

        # load the device_state file
        # set serial
        await system.unstable.stash.set(
            f"/profile/nodes/proxy_device_host_usb/device_states/{device_state_idx}/key",
            tritium_serial,
        )
        # set data
        await system.unstable.stash.set(
            f"/profile/nodes/proxy_device_host_usb/device_states/{device_state_idx}/value",
            config["device_states"],
        )

    def get_device_local_config(self, devices, device_states, serial):
        if serial is None:
            return None

        config = {"device_states": None, "device_customization": None}
        for ds in device_states:
            if type(ds) is dict and "key" in ds and serial == ds["key"]:
                config["device_states"] = ds["value"]
                break
        for d in devices:
            if type(d) is dict and "key" in d and serial == d["key"]:
                config["device_customization"] = d["value"]
                break
        return config

    # Hacky way to reset device to force it to reenumerate
    def reset_device(self, tritium_name):
        if tritium_name.startswith("USB BDC"):
            serial_id = self.dcc_manager.get_serial_id(tritium_name)
            os.system(f"sudo dfu-util -e -S {serial_id}")

    """
    Update all the board configs from the cloud
    """

    async def pull_all_configs_from_cloud(self, filter=None):
        for d in system.unstable.owner.device_manager.devices:
            if d.identifier.startswith("proxy_device_host_usb_") and d.online:
                tritium_name = d.logical_name
                tritium_serial = d._last_cfg["serial"]

                cloud_config = self.dcc_manager.get_config(tritium_serial)
                if cloud_config is not None:
                    log.info(f"Fetching cloud config for {tritium_name}")
                    await self.configure_device_from_config(tritium_name, cloud_config)

    async def pull_config_from_cloud(self, board):
        for d in system.unstable.owner.device_manager.devices:
            if d.identifier.startswith("proxy_device_host_usb_") and d.online:
                tritium_name = d.logical_name
                tritium_serial = d._last_cfg["serial"]
                if tritium_name == board or tritium_serial == board:
                    cloud_config = self.dcc_manager.get_config(tritium_serial)
                    if cloud_config is not None:
                        log.info(f"Fetching cloud config for {tritium_name}")
                        await self.configure_device_from_config(
                            tritium_name, cloud_config
                        )
                    else:
                        log.warning(
                            "Cannot find config for {tritium_nane} in the cloud"
                        )

    async def pull_unconfigured_configs(self):
        for d in system.unstable.owner.device_manager.devices:
            if d.identifier.startswith("proxy_device_host_usb_") and d.online:
                # if tritium name ends with a serial number
                # the board is likely not configured
                tritium_name = d.logical_name
                tritium_serial = d._last_cfg["serial"]
                config = self.get_device_local_config(
                    self.devices, self.device_states, tritium_serial
                )

                if config is None or config["device_states"] is None:
                    cloud_config = self.dcc_manager.get_config(tritium_serial)
                    if cloud_config is not None:
                        log.info(f"Fetching cloud config for {tritium_name}")
                        await self.configure_device_from_config(
                            tritium_name, cloud_config
                        )
                        # self.reset_device(tritium_name)
                    else:
                        log.warning(f"Cloud config not found for {tritium_name}")
                        pass
                else:
                    log.warning(f"Device already has a config {tritium_name}")

    """
    Get the Controls from the cloud and update stash, restart is needed
    robot is the type of robot: Ameca
    """

    async def load_controls_from_cloud(self, robot):
        controls = self.dcc_manager.get_default_controls("Ameca")
        if controls is None:
            log.warning("Cannot find {robot} controls int the cloud")
            return False

        log.info(f"Setting stash /profile/robot/controls to {controls}")
        await system.unstable.stash.set("/profile/robot/controls/", controls)

    async def pull_generic_config(self, robot, board, device_id):
        for d in system.unstable.owner.device_manager.devices:
            if d.identifier.startswith("proxy_device_host_usb_") and d.online:
                tritium_name = d.logical_name
                tritium_serial = d._last_cfg["serial"]

                if str(tritium_serial) == device_id:
                    log.info(
                        f"Fetching generic {robot} {board} config for {tritium_serial}"
                    )
                    cloud_config = self.dcc_manager.get_default_config(robot, board)
                    await self.configure_device_from_config(
                        tritium_serial, cloud_config
                    )

    async def push_device_configs(self, OVERWRITE_FLAG=False):
        # Get the online devices
        for d in system.unstable.owner.device_manager.devices:
            if d.identifier.startswith("proxy_device_host_usb_") and d.online:
                tritium_name = d.logical_name
                tritium_serial = d._last_cfg["serial"]

                if tritium_serial:
                    tritium_serial = str(tritium_serial)
                    config = self.get_device_local_config(
                        self.devices, self.device_states, tritium_serial
                    )
                    cloud_config = self.dcc_manager.get_config(tritium_serial)
                    if config is not None:
                        if cloud_config is None or OVERWRITE_FLAG:
                            log.info(
                                f"uploading config for {tritium_name} ({tritium_serial})"
                            )
                            await self.dcc_manager.add_config(
                                tritium_serial, config, OVERWRITE_FLAG
                            )

    async def swap_board_serial(self, board_name, tritium_serial_new):
        # Check if new tritium_serial is valid
        if not self.dcc_manager.contains_valid_serial_id(tritium_serial_new):
            log.warning(f"New device ID doesn't seem valid: {tritium_serial_new}")

        # Try to find the old device's serial
        for d in self.devices:
            tritium_name = d["value"]["name"]
            tritium_serial_old = d["key"]

            if self.dcc_manager.contains_valid_serial_id(tritium_serial_old):
                if tritium_name == board_name:
                    # We found the old board, get the config
                    log.info(
                        f"Old board serial found: {tritium_name}  - {tritium_serial_old}"
                    )
                    old_config = self.get_device_local_config(
                        self.devices, self.device_states, tritium_serial_old
                    )
                    # Check if config is valid
                    if (
                        old_config["device_states"] is not None
                        and old_config["device_customization"] is not None
                    ):
                        # Swap the serial to the new one
                        log.info(
                            f"Changing old serial to new serial: {tritium_serial_old} -> {tritium_serial_new} "
                        )
                        await self.configure_device_from_config(
                            tritium_serial_new, old_config, tritium_serial_old
                        )
                    else:
                        log.warning(
                            f"Cannot load config for: {tritium_name}  - {tritium_serial}"
                        )
                    break

    async def compare_to_generic_config(
        self, robot, board, compare_only=False, ignore_filter=None
    ):
        for d in system.unstable.owner.device_manager.devices:
            if d.identifier.startswith("proxy_device_host_usb_") and d.online:
                tritium_name = d.logical_name
                tritium_serial = d._last_cfg["serial"]
                # print(tritium_name)
                # print(tritium_serial)

                if str(tritium_name) == board:
                    log.info(
                        f"Fetching generic {robot} {board} config and comparing it with {tritium_serial}"
                    )
                    cloud_config = self.dcc_manager.get_default_config(robot, board)
                    local_config = self.get_device_local_config(
                        self.devices, self.device_states, tritium_serial
                    )
                    if cloud_config is not None:
                        if ignore_filter is not None:
                            updated_config = self.compare_configs.compare_configs(
                                cloud_config,
                                local_config,
                                verbose=True,
                                ignore_filter=ignore_filter,
                            )
                        else:
                            updated_config = self.compare_configs.compare_configs(
                                cloud_config, local_config, verbose=True
                            )
                        if compare_only == False:
                            # Update the customizations too
                            updated_config["device_customization"] = cloud_config[
                                "device_customization"
                            ]
                            await self.configure_device_from_config(
                                tritium_serial, updated_config
                            )

    @system.tick(fps=1)
    async def on_tick(self):
        self.dcc_manager.pull_repo()
        self.devices = await stash.get("/profile/nodes/proxy_device_host_usb/devices")
        self.device_states = await stash.get(
            "/profile/nodes/proxy_device_host_usb/device_states"
        )
        # await self.push_device_configs(OVERWRITE_FLAG=True)
        # await self.pull_all_configs_from_cloud()
        # await self.pull_config_from_cloud("USB BDC 377335723039")
        # await self.pull_unconfigured_configs()
        # await self.swap_board_serial("Torso Motor Board", "USB BDC 206B36755643")
        # await self.pull_generic_config("Ameca", "Torso Motor Board", "USB BDC 205736755643")
        # COMPARE_ONLY = False
        # await self.compare_to_generic_config("Ameca", "Eyeball Right Motor Board", COMPARE_ONLY, ignore_filter=[])
        # await self.compare_to_generic_config("Ameca", "Eyeball Left Motor Board", COMPARE_ONLY, ignore_filter=[])
        # await self.compare_to_generic_config("Ameca", "Torso Motor Board", COMPARE_ONLY)
        # await self.compare_to_generic_config("Ameca", "Brows Motor Board", COMPARE_ONLY)

        # Do not use this if you're unsure if this robot is unusual
        # await self.load_controls_from_cloud("Ameca")

        # self.dcc_manager.push_repo()
        self.stop()
