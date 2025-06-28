"""
 This control functions intended use is to wait for the homing motion in the Lips of the Ameca G2 head.
 To do so it is doing the following steps:

1. Disable motor voltage for head boards.
2. Wait for all the boards to come online and be ready OR if the missing board timeout has expired.
3. Enable motor voltage
4. Check if homing is required
5. Do homing if required
6. Leave Startup state when homing is ready or when the missing board timeout has expired.
7. Monitors the presence of the boards -> When one of them disappears enters into Startup state.


 Changes:
     0.0.1: Initial release
     2.0.0: Re-write it
     2.0.1: Check all the head controls
     2.0.2: Do not rehome on face thermal error
     2.1.0: Automatically re-home when the user switches back to startup state
     2.1.1: Use same script for both desktop and full-body
     2.1.2: Do not rehome if robot is in stopped state, wait for user to change state first

     TODO:
     * Check for wrist yaw homing for full-body
"""

import asyncio
from time import monotonic

from tritium.robot.device.exceptions import (
    DeviceNotFoundError,
    InvalidParameterNameError,
)

REHOME_SCRIPT_NAME = "./Re-home Head Motors.py"
start_other_script = system.import_library("./utils.py").start_other_script
is_other_script_running = system.import_library("./utils.py").is_other_script_running
tritium_version = system.import_library("../Utils/versions.py").tritium_version


BOARDS_TO_WAIT_FOR = [
    "Lips Left and Bottom Motor Board",
    "Lips Right and Top Motor Board",
    "Head Yaw Jaw and Nose Motor Board",
    "Eyeball Left Motor Board",
    "Eyeball Right Motor Board",
    "Brows Motor Board",
]
ENABLE_PARAM = "General.Config.Enable Motor"
HOMING_FAILURE_TIMEOUT = 30
BOARD_ONLINE_TIMEOUT = 25

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
controls = {
    c: system.control(c, None, ["status", "abs_flag", "error"]) for c in direct_controls
}

head_power = system.control("Head Power", None, ["vcontrol_voltage", "vmotor_voltage"])
VOLTAGE_THRESHOLD = 19  # V


class Activity:
    @property
    def state_engine(self):
        return system.unstable.state_engine

    def enable_boards(self, flag):
        waiting_for = set(BOARDS_TO_WAIT_FOR)
        dm = system.unstable.owner.device_manager
        for d in dm.devices:
            if d.online and d.logical_name in waiting_for:
                p = d.get_parameter_by_name_in_device_class(ENABLE_PARAM)
                p.demand = flag
                waiting_for.discard(d.logical_name)
        probe("devices", f"didn't trigger {waiting_for}")
        return not waiting_for

    def all_devices(self):
        return system.unstable.owner.device_manager.devices

    def get_parameter(self, device_name, parameter_name):
        d = system.unstable.owner.device_manager.get_device_by_name(device_name)
        return d.get_parameter_by_name(parameter_name)

    def online_device_names(self):
        return {
            d.logical_name
            for d in system.unstable.owner.device_manager.devices
            if d.online
        }

    def is_board_online(self, name):
        for d in self.all_devices():
            if d.identifier == name:
                if d._online:
                    return True
        return False

    def apply_pose(self, pose_name):
        pose = system.poses.get(pose_name)
        if not pose:
            probe("MISSING POSE", pose)
        else:
            print("applying pose", pose_name)
            system.poses.apply(pose)

    def smile(self):
        # Apply a pose that makes the face look normal
        self.apply_pose("Mouth Happy")

    def is_all_board_online(self):
        all_online = True
        online_names = self.online_device_names()
        for b in BOARDS_TO_WAIT_FOR:
            online = b in online_names
            probe(b, online)

            if not online:
                all_online = False

        return all_online

    def motors_should_have_power(self):
        if (
            not head_power.vcontrol_voltage
            or head_power.vcontrol_voltage < VOLTAGE_THRESHOLD
        ):
            probe(
                "not started due to",
                f"head_power.vcontrol_voltage {head_power.vcontrol_voltage!r}",
            )
            return False
        probe("not started due to", "-")
        return True

    def are_motor_boards_initialised(self):
        for ctrl in controls:
            if controls[ctrl].status == 5:
                return False
        return True

    def is_homing_finished(self):
        for ctrl in controls:
            if controls[ctrl].status != 0:
                probe("not finished due to", f"{ctrl}.status = {controls[ctrl].status}")
                return False
            if not controls[ctrl].abs_flag:
                probe("not finished due to", f"{ctrl}.abs_flag is False")
                return False
        # probe("not finished due to", "-")
        return True

    def should_we_rehome(self):
        now = monotonic()
        probe("rehome_cntr", self.rehome_cntr)
        probe("time since last non-forced rehome (sec)", (now - self.last_rehome_time))
        rehome_reason = None
        for ctrl in controls:
            # We look for errors instead of status here, cause status
            # includes thermal limit triggers which we aren't fatal
            # enough to warrant re-homing.
            if controls[ctrl].error != 0:
                rehome_reason = f"{ctrl}.error"
            if not controls[ctrl].abs_flag:
                rehome_reason = f"{ctrl}.abs_flag"

            # Max one rehome in 60 secs
            if rehome_reason is not None and now - self.last_rehome_time > 60:
                # Do not rehome for the same reason twice
                if self.prev_rehome_reason == rehome_reason:
                    probe("skipped rehome (because duplicated reason)", rehome_reason)
                else:
                    probe("rehomed due to", rehome_reason)
                    probe("rehomed due to (prev)", self.prev_rehome_reason)
                    self.prev_rehome_reason = rehome_reason
                    self.last_rehome_time = now
                    self.rehome_cntr += 1

                    return True

        if is_other_script_running(system, REHOME_SCRIPT_NAME):
            rehome_reason = "Re-home script is running."
            probe("rehomed due to", rehome_reason)
            self.prev_rehome_reason = rehome_reason
            # self.last_rehome_time = now
            return True

        # Something triggered a rehome by setting the state to startup
        if self.state_engine.operational_mode_identifier == "startup":
            rehome_reason = "Robot state set to startup"
            probe("rehomed due to", rehome_reason)
            self.prev_rehome_reason = rehome_reason
            # self.last_rehome_time = now
            return True

        return False

    def set_param_demand(self, device, param, demand):
        try:
            self.get_parameter(device, param).demand = demand
        except (InvalidParameterNameError, DeviceNotFoundError):
            print(f"Error: Parameter not found: {device!r}, {param!r}")

    def enter_idle_state(self):
        if self.state_engine.operational_mode_identifier == "startup":
            print("ENTERING ACTIVE")
            self.state_engine.enter_operational_mode(
                self.state_before_home,
                "All boards online.",
            )
            self.apply_pose("Mouth Neutral")

    def enter_startup_state(self):
        if self.state_engine.operational_mode_identifier != "startup":
            print("RETURNING TO STARTUP")
            self.state_engine.enter_operational_mode(
                "startup", "Some of the boards disappeared"
            )

    def check_state(self):
        # we want to make sure state before home never gets set to startup
        # otherwise once we have homed we will go back to startup and home
        # again forever
        probe("state before homing", self.state_before_home)
        state = self.state_engine.operational_mode_identifier
        if state != "startup":
            self.state_before_home = state

    async def on_start(self):
        # Count number of rehomes
        self.rehome_cntr = 0
        self.last_rehome_time = 0
        self.prev_rehome_reason = None
        self.state_before_home = "idle" if tritium_version() == "3.0" else "active"

        head_power.vmotor_enable = False
        probe("state", "waiting for boards")
        await self.wait_for_all_boards()

        forced_rehome = False
        while True:
            await self.run_startup_process(forced_rehome)
            # Wait for operational mode to enter active when homing was success
            await asyncio.sleep(0.5)
            forced_rehome = False
            probe("state", "started up, watching for failure")
            # Wait forever whilst all the boards are online
            while self.is_all_board_online() or self.state_before_home == "stopped":
                # also check for failure
                if self.should_we_rehome() and self.state_before_home != "stopped":
                    forced_rehome = True
                    break
                # if in stopped state DO NOT exit this loop. User set stopped
                # state to work on robot, dangerous to suddenly start rehoming
                self.check_state()
                await asyncio.sleep(1.5)

            # Switch off head VMotor
            head_power.vmotor_enable = False
            # If a board dissappears we restart the homing process
            # Wait for the boards to be back before actually leaving current state
            probe("state", "board failed, waiting for boards")
            await self.wait_for_all_boards()
            # Stop the robot by going into startup state
            self.enter_startup_state()
            # Loop round and re-home

    async def run_startup_process(self, forced_rehome=False):
        probe("state", "starting up")
        # Switch on head VMotor before homing sequence

        head_power.vmotor_enable = True
        if not self.is_homing_finished() or forced_rehome:
            probe("state", "homing")
            homed = await self.home_head()
            if not homed:
                log.error("HEAD HOMING TIMEOUT: RETRYING ONCE")
                homed = await self.home_head()
        else:
            homed = True

        probe("state", f"homing finished, success: {homed}")
        # Enable boards here too in case the persistent state is disabled and no homing sequence was run.
        self.enable_boards(True)
        await asyncio.sleep(0.5)
        if homed:
            self.smile()
        await asyncio.sleep(1.5)
        probe("state", f"entering previous state {self.state_before_home}")
        self.enter_idle_state()

    async def wait_for_all_boards(self):
        start_time = monotonic()
        while not self.motors_should_have_power():
            probe("state", "waiting vcontrol power")
            await asyncio.sleep(0.5)
        while not self.is_all_board_online():
            probe("state", "waiting for boards to be online")
            if monotonic() - start_time > HOMING_FAILURE_TIMEOUT:
                log.error("HEAD HOMING TIMEOUT: BOARDS NOT ALL ONLINE")
                break
            await asyncio.sleep(0.5)

        # The motor boards are going through an initialisation phase after they are connected to tritium.
        # Wait for that until it finishes.
        while not self.are_motor_boards_initialised():
            probe("state", "waiting for boards to be initialised")
            if monotonic() - start_time > HOMING_FAILURE_TIMEOUT:
                log.error("HEAD HOMING TIMEOUT: Not all boards are initialised.")
                break

            await asyncio.sleep(0.5)

    async def home_head(self):
        start_time = monotonic()
        if not is_other_script_running(system, REHOME_SCRIPT_NAME):
            start_other_script(system, REHOME_SCRIPT_NAME)
        # Wait for the script to startup
        await asyncio.sleep(0.5)
        # Check if homing is done and script is still running
        while not self.is_homing_finished() or is_other_script_running(
            system, REHOME_SCRIPT_NAME
        ):
            if monotonic() - start_time > HOMING_FAILURE_TIMEOUT:
                log.error("HEAD HOMING TIMEOUT: HOMING MOTION FAILED")
                return False
            await asyncio.sleep(0.5)
        return True
