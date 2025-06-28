import asyncio

ABS_FLAG_PARAM = "General.Config.Clear Abs Flags"
ENABLE_PARAM = "General.Config.Enable Motor"

BOARDS_TO_RESET = [
    "Lips Left and Bottom Motor Board",
    "Lips Right and Top Motor Board",
    "Head Yaw Jaw and Nose Motor Board",
    "Eyeball Left Motor Board",
    "Eyeball Right Motor Board",
    "Brows Motor Board",
]

direct_controls = [
    "Jaw Left Motor",
    "Jaw Right Motor",
    "Lip Top Corner Left Motor",
    "Lip Top Corner Right Motor",
    "Lip Bottom Corner Left Motor",
    "Lip Bottom Corner Right Motor",
    "Lip Bottom Depress Left",
    "Lip Bottom Depress Right",
    "Lip Bottom Depress Middle",
    "Lip Top Raise Left",
    "Lip Top Raise Middle",
    "Lip Top Raise Right",
    "Lip Top Curl",
    "Lip Bottom Curl",
]

head_power = system.control("Head Power", None, ["vcontrol_voltage", "vmotor_voltage"])
VOLTAGE_THRESHOLD = 19

controls = {
    c: system.control(c, None, ["status", "abs_flag", "error"]) for c in direct_controls
}

jaw_pitch = system.control("Jaw Pitch", None)


class Activity:
    def find_device_by_name(self, name):
        dm = system.unstable.owner.device_manager
        for d in dm.devices:
            if d.logical_name == name:
                return d

    def acquire_enable_params(self):
        self.acquired_params = []
        waiting_for = set(BOARDS_TO_RESET)
        dm = system.unstable.owner.device_manager
        for d in dm.devices:
            if d.online and d.logical_name in waiting_for:
                p = d.get_parameter_by_name_in_device_class(ENABLE_PARAM)
                self.acquired_params.append(p)
                waiting_for.discard(d.logical_name)
        system.unstable.owner.device_manager.acquire_parameters(self.acquired_params)
        # print("ACQUIRED PARAMS", self.acquired_params)
        return not waiting_for

    def release_enable_params(self):
        system.unstable.owner.device_manager.release_parameters(self.acquired_params)
        # print("RELEASED PARAMS", self.acquired_params)
        self.acquired_params = []

    def is_all_motors_enabled(self):
        all_enabled = True
        for p in self.acquired_params:
            paramname = f"{p.device}.{p.name}"
            probe(paramname, p.value)
            if p.value is False:
                all_enabled = False
        return all_enabled

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

    def clear_flags_on_all_devices(self, flag):
        waiting_for = set(BOARDS_TO_RESET)
        dm = system.unstable.owner.device_manager
        for d in dm.devices:
            if d.online and d.logical_name in waiting_for:
                p = d.get_parameter_by_name_in_device_class(ABS_FLAG_PARAM)
                p.demand = flag
                waiting_for.discard(d.logical_name)
        probe("devices", f"didn't trigger {waiting_for}")
        return not waiting_for

    async def clear_errors(self):
        ctrls_to_enable = []
        # Disable errored out channels
        for ctrl in controls:
            if controls[ctrl].error != 0:
                controls[ctrl].enable = False
                ctrls_to_enable.append(ctrl)

        await asyncio.sleep(0.1)
        # Enabled th errored out channels
        for ctrl in ctrls_to_enable:
            controls[ctrl].enable = True

    def is_all_motors_ready_to_home(self):
        if (
            not head_power.vmotor_voltage
            or head_power.vmotor_voltage < VOLTAGE_THRESHOLD
        ):
            probe(
                "not started due to",
                f"head_power.vmotor_voltage {head_power.vmotor_voltage!r}",
            )
            return False

        for ctrl in controls:
            # Motor is ready to home when status is:
            # * Ready state
            # * Abs reset in progress state
            if controls[ctrl].status != 0 and controls[ctrl].status != 1:
                return False
        return True

    def is_homing_finished(self):
        for ctrl in controls:
            if controls[ctrl].status != 0:
                probe("not finished due to", f"{ctrl}.status")
                return False
            if controls[ctrl].abs_flag == False:
                probe("not finished due to", f"{ctrl}.abs_flag")
                return False

        probe("not finished due to", "-")
        return True

    async def on_start(self):
        self.acquired_params = []
        await self.rehome()
        self.stop()

    def on_stop(self):
        self.release_enable_params()

    async def rehome(self):
        probe("re-home head", "STARTING")

        await self.clear_errors()

        while self.acquire_enable_params() is False:
            probe("not finished due to", "waiting for boards")
            await asyncio.sleep(1)

        # Wait until all boards are disabled
        while self.enable_boards(False) is False:
            probe("not finished due to", "waiting for boards")
            await asyncio.sleep(1)

        await asyncio.sleep(0.1)

        # Wait for motors to be ready to start homing
        while not self.is_all_motors_ready_to_home():
            await asyncio.sleep(0.5)

        self.clear_flags_on_all_devices(True)
        await asyncio.sleep(0.3)
        self.clear_flags_on_all_devices(False)

        # Check if the enable motor params are set
        self.enable_boards(True)
        await asyncio.sleep(0.5)
        # Try to enable params until it succeeds
        while self.is_all_motors_enabled() is not True:
            self.enable_boards(True)
            await asyncio.sleep(0.5)

        probe("re-home head", "TRIED")

        while not self.is_homing_finished():
            await asyncio.sleep(1)
        probe("re-home head", "DONE")