"""
Sets the Enable Motors parameter for the head board to False
They need to be False so they homing won't start automatically when the head comes online.
The SYS_Startup_State will sync them together.
"""

import asyncio

ENABLE_PARAM = "General.Config.Enable Motor"

BOARDS_TO_RESET = [
    "Lips Left and Bottom Motor Board",
    "Lips Right and Top Motor Board",
    "Head Yaw Jaw and Nose Motor Board",
    "Eyeball Left Motor Board",
    "Eyeball Right Motor Board",
    "Brows Motor Board",
]


class Activity:

    def enable_boards(self, flag):
        waiting_for = set(BOARDS_TO_RESET)
        dm = system.unstable.owner.device_manager
        for d in dm.devices:
            if d.online and d.logical_name in waiting_for:
                p = d.get_parameter_by_name_in_device_class(ENABLE_PARAM)
                p.demand = flag
                waiting_for.discard(d.logical_name)
        probe("devices", f"didn't trigger {waiting_for}")
        return not waiting_for

    async def save_parameters(self):
        for d in BOARDS_TO_RESET:
            device = system.unstable.owner.device_manager.get_device_by_name(d)
            for dh in system.unstable.owner.device_manager.device_hosts:
                if device in dh.devices:
                    host = dh
            await host.client.call_api("save_parameters", deviceID=device.id)

    async def on_start(self):
        self.enable_boards(False)
        await asyncio.sleep(1)
        await self.save_parameters()
        self.enable_boards(True)
        self.stop()
        pass

    def on_stop(self):
        pass