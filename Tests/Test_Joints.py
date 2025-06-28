"""
    This script tests all joints on a robot. It ensures that it reaches the expected position and that the current is within an expected threshold


    Version 0.0.1
    Changes:
        0.0.1: Initial release
"""

# flake8: noqa  (disabling linter completely, no way to remove just for a block of code, and getting lots of E241 because of the )
import asyncio

from tritium.robot.device.exceptions import ControlPropertyNotFoundError

CONFIG = system.import_library("../Config/HB3.py").CONFIG
FULL_SIZE = CONFIG["ROBOT_TYPE"] == CONFIG["ROBOT_TYPES"].AMECA

# Logs the currents and positions even when tests pass
VERBOSE = False

# Vocalise warnings and failed tests
USE_TTS = False

# Change this to the name of a test if you want too run only one specified test
TEST_OVERRIDE = None

MOVE_FPS = 10
TEST_FPS = 20

MOVE_TIME_S = 1
HOLD_BEFORE_TEST_TIME_S = 1
TEST_TIME_S = 2

WAIT_AFTER_TTS_S = 5

MOVE_SLEEP_TIME_S = 1 / MOVE_FPS
TEST_SLEEP_TIME_S = 1 / TEST_FPS

PARAMS_TO_ACQUIRE = ("current", "min", "max", "position")

SCRIPTS_TO_STOP = [
    "HB3/HB3_Controller.py",
    "HB3/Chat_Controller.py",
    # Drivers are in HB3 on older scripts:
    "HB3/Drivers/Brows.py",
    "HB3/Drivers/Eyelids.py",
    "HB3/Drivers/Gaze_Target.py",
    "HB3/Drivers/Mouth.py",
    # Drivers are in System on newer scripts:
    "System/Driver/Brows.py",
    "System/Drivers/Eyelids.py",
    "System/Drivers/Gaze_Target.py",
    "System/Drivers/Mouth.py",
]

SCRIPTS_TO_START = [
    "HB3/Actuation/Do_TTS.py"  # Used to make the robot say if there are any errors, and warn before raising hands
]

# fmt: off

# Controls to test
# |     Control                |     Namespace     |  Default | Current Limit | Current Limit | Joint Position |
# |      Name                  |                   | Position |  at Min Pos   |  at Max Pos   |   Threshold    |                                  
COMMON_JOINT_CONTROLS = [
    ("Brow Inner Left",               None,             0.65,   0.10,   0.03,   0.02),
    ("Brow Inner Right",              None,             0.65,   0.10,   0.03,   0.02),
    ("Brow Outer Left",               None,             0.65,   0.04,   0.04,   0.02),
    ("Brow Outer Right",              None,             0.65,   0.04,   0.04,   0.02),
    ("Eye Pitch Left Motor",          None,             97.4,   0.03,   0.10,   0.1), 
    ("Eye Pitch Right Motor",         None,             87.3,   0.03,   0.10,   0.1),
    ("Eye Yaw Left Motor",            None,             95.6,   0.08,   0.08,   0.2),
    ("Eye Yaw Right Motor",           None,             93.9,   0.08,   0.08,   0.2),
    ("Eyelid Lower Left",             None,             14,     0.03,   0.03,   0.07),
    ("Eyelid Lower Right",            None,             14,     0.03,   0.03,   0.07),
    ("Eyelid Upper Left",             None,             14,     0.12,   0.01,   0.07),
    ("Eyelid Upper Right",            None,             14,     0.12,   0.01,   0.07),
    ("Lip Bottom Corner Left Motor",  None,             0.55,   0.13,   0.10,   0.07),
    ("Lip Bottom Corner Right Motor", None,             0.55,   0.13,   0.10,   0.07),
    ("Lip Top Corner Left Motor",     None,             0.55,   0.08,   0.09,   0.05),
    ("Lip Top Corner Right Motor",    None,             0.55,   0.08,   0.09,   0.05),
    ("Lip Bottom Curl",               None,             0.46,   0.05,   0.08,   0.01),
    ("Lip Bottom Depress Left",       None,             0.55,   0.05,   0.06,   0.01),
    ("Lip Bottom Depress Middle",     None,             0.43,   0.05,   0.05,   0.01),
    ("Lip Bottom Depress Right",      None,             0.55,   0.05,   0.06,   0.01),
    ("Lip Top Curl",                  None,             0.41,   0.05,   0.15,   0.01),
    ("Lip Top Raise Left",            None,             0.48,   0.05,   0.05,   0.01),
    ("Lip Top Raise Middle",          None,             0.47,   0.05,   0.17,   0.01),
    ("Lip Top Raise Right",           None,             0.48,   0.05,   0.05,   0.01),
    ("Jaw Left Motor",                None,             45,     0.09,   0.09,   0.8),
    ("Jaw Right Motor",               None,             45,     0.09,   0.09,   0.8),
    ("Neck Front Left Motor",         None,             16.4,   0.3,   0.3,   3.0), 
    ("Neck Front Right Motor",        None,             16.4,   0.3,   0.3,   3.0),
    ("Neck Rear Left Motor",          None,             21.5,   0.3,   0.3,   3.0),
    ("Neck Rear Right Motor",         None,             21.5,   0.3,   0.3,   3.0),
    ("Head Yaw",                      "Mesmer Neck 1",  0,      0.20,   0.20,   1),
    ("Nose Wrinkle",                  "Mesmer Nose 1",  0.01,   0.06,   0.10,   0.01),
]

# |     Control                |     Namespace     |  Default | Current Limit | Current Limit | Joint Position |
# |      Name                  |                   | Position |     Min Pos   |    Max Pos    |   Threshold    | 
FULL_SIZE_ONLY_JOINT_CONTROLS = [
    ("Torso Left Motor",              None,               31,    0.70,   0.70,   0.50),
    ("Torso Right Motor",             None,               31,    0.70,   0.70,   0.50),
    ("Torso Yaw",                     "Mesmer Torso 1",   0,     0.30,   0.30,   0.40),
    ("Wrist Left Inner Motor",        None,               14,    0.03,   0.03,   0.30),
    ("Wrist Left Outer Motor",        None,               14,    0.03,   0.03,   0.30),
    ("Wrist Right Outer Motor",       None,               14,    0.03,   0.03,   0.30),
    ("Wrist Right Inner Motor",       None,               14,    0.03,   0.03,   0.30),
    ("Elbow Pitch Left",              "Mesmer Arms 1",    10,    0.07,   0.70,   0.60),
    ("Elbow Pitch Right",             "Mesmer Arms 1",    10,    0.07,   0.70,   0.60),
    ("Wrist Yaw Left",                "Mesmer Arms 1",    80,    0.01,   0.01,   1.50),
    ("Wrist Yaw Right",               "Mesmer Arms 1",    80,    0.01,   0.01,   1.50),
    ("Clavicle Roll Left",            "Mesmer Arms 1",    0,     0.20,   0.35,   0.10),
    ("Clavicle Roll Right",           "Mesmer Arms 1",    0,     0.20,   0.35,   0.10),
    ("Clavicle Yaw Left",             "Mesmer Arms 1",    0,     0.40,   1.50,   0.50),
    ("Clavicle Yaw Right",            "Mesmer Arms 1",    0,     0.40,   1.50,   0.50),
    ("Shoulder Pitch Left",           "Mesmer Arms 1",    10,    0.4,   0.80,   0.45),
    ("Shoulder Pitch Right",          "Mesmer Arms 1",    10,    0.4,   0.80,   0.45),
    ("Shoulder Roll Left",            "Mesmer Arms 1",    10,    0.10,   2.50,   2.50),
    ("Shoulder Roll Right",           "Mesmer Arms 1",    10,    0.10,   2.50,   2.50),
    ("Shoulder Yaw Left",             "Mesmer Arms 1",    0,     0.25,   0.35,   5.00),
    ("Shoulder Yaw Right",            "Mesmer Arms 1",    0,     0.25,   0.35,   5.00),
    ("Index Finger Left",             "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Little Finger Left",            "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Middle Finger Left",            "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Ring Finger Left",              "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Index Finger Right",            "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Little Finger Right",           "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Middle Finger Right",           "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
    ("Ring Finger Right",             "Mesmer Fingers 1", 0.8,   0.10,   0.01,   0.02),
]

# Controls that switch between high level control and direct joint control

# |     Control               |  Namespace |    Default Differential Mode    |
# |      Name                 |            | 1 - Differential, 2 - Four Axis | 
COMMON_DIFFERENTIAL_MODE_CONTROLS = [
    ("Eye Left High Level",      None,          2),
    ("Eye Right High Level",     None,          2),
    ("Lips Left High Level",     None,          1),
    ("Lips Right High Level",    None,          1),
    ("Jaw High Level",           None,          1),
    ("Neck High Level",          None,          2),
]

# |     Control               |  Namespace |    Default Differential Mode    |
# |      Name                 |            | 1 - Differential, 2 - Four Axis | 
FULL_SIZE_ONLY_DIFFERENTIAL_MODE_CONTROLS = [
    ("Torso High Level",         None,          2),
    ("Wrist Left High Level",    None,          2),
    ("Wrist Right High Level",   None,          2),
]

# Test definitions. Can test multiple controls at once, and can set other controls to specific positions to prevent collisions. 
# The rest of the controls will be at the default position defined earlier

## Common Tests

# |        Test          |  Dict of Controls                                                |    Positions for other controls    |
# |        Name          |  And which limit is tested ("min"/"max")                         |       If required for test         | 
EYELID_TESTS = [
    ("Upper Eyelids Max",     {"Eyelid Upper Left": "max", "Eyelid Upper Right": "max"},      {"Eyelid Lower Left": 0, "Eyelid Lower Right": 0}),
    ("Upper Eyelids Min",     {"Eyelid Upper Left": "min", "Eyelid Upper Right": "min"},      {}),
    ("Lower Eyelids Max",     {"Eyelid Lower Left": "max", "Eyelid Lower Right": "max"},      {"Eyelid Upper Left": 0, "Eyelid Upper Right": 0}),
    ("Lower Eyelids Min",     {"Eyelid Lower Left": "min", "Eyelid Lower Right": "min"},      {}),
]

EYE_TESTS = [
    ("Eye Yaw Max",           {"Eye Yaw Left Motor": "max", "Eye Yaw Right Motor": "max"},    {}),
    ("Eye Yaw Min",           {"Eye Yaw Left Motor": "min", "Eye Yaw Right Motor": "min"},    {}),
    ("Eye Pitch Max",         {"Eye Pitch Left Motor": "max", "Eye Pitch Right Motor": "max"},{}),
    ("Eye Pitch Min",         {"Eye Pitch Left Motor": "min", "Eye Pitch Right Motor": "min"},{}),
]

BROW_TESTS = [
    ("Brows Max",             {"Brow Inner Left": "max", "Brow Inner Right": "max", "Brow Outer Left": "max", "Brow Outer Right": "max"},  {}),
    ("Brows Min",             {"Brow Inner Left": "min", "Brow Inner Right": "min", "Brow Outer Left": "min", "Brow Outer Right": "min"},  {})
]

NOSE_TESTS = [
    ("Nose Max",              {"Nose Wrinkle": "max"},                                        {}),
    ("Nose Min",              {"Nose Wrinkle": "min"},                                        {}),
]

JAW_TESTS = [
    ("Jaw Left Max",          {"Jaw Left Motor": "max"},                                      {}),
    ("Jaw Left Min",          {"Jaw Left Motor": "min"},                                      {"Jaw Right Motor": 70}),
    ("Jaw Right Max",         {"Jaw Right Motor": "max"},                                     {}),
    ("Jaw Right Min",         {"Jaw Right Motor": "min"},                                     {"Jaw Left Motor": 70}),
]

LIP_TESTS = [
    ("Lip Top Max",           {"Lip Top Raise Middle": "max", "Lip Top Raise Left": "max", "Lip Top Raise Right": "max", "Lip Top Curl": "max"},  {}),
    ("Lip Top Min",           {"Lip Top Raise Middle": "min", "Lip Top Raise Left": "min", "Lip Top Raise Right": "min", "Lip Top Curl": "min"},  {"Jaw Right Motor": 50, "Jaw Left Motor": 50}),
    ("Lip Top Corners Max",   {"Lip Top Corner Left Motor": "max", "Lip Top Corner Right Motor": "max"},                                          {}),
    ("Lip Top Corners Min",   {"Lip Top Corner Left Motor": "min", "Lip Top Corner Right Motor": "min"},                                          {}),
    ("Lip Bottom Corners Max",{"Lip Bottom Corner Left Motor": "max", "Lip Bottom Corner Right Motor": "max"},                                    {}),
    ("Lip Bottom Corners Min",{"Lip Bottom Corner Left Motor": "min", "Lip Bottom Corner Right Motor": "min"},                                    {}),
    ("Lip Bottom Max",        {"Lip Bottom Depress Middle": "max", "Lip Bottom Depress Left": "max", "Lip Bottom Depress Right": "max", "Lip Bottom Curl": "max"},  {}),
    ("Lip Bottom Min",        {"Lip Bottom Depress Middle": "min", "Lip Bottom Depress Left": "min", "Lip Bottom Depress Right": "min", "Lip Bottom Curl": "min"},  {"Jaw Right Motor": 50, "Jaw Left Motor": 50}),
]

NECK_TESTS = [
    ("Neck Front Max",        {"Neck Front Left Motor": "max", "Neck Front Right Motor": "max"}, {"Neck Rear Left Motor": 15, "Neck Rear Right Motor": 15}),
    ("Neck Front Min",        {"Neck Front Left Motor": "min", "Neck Front Right Motor": "min"}, {"Neck Rear Left Motor": 19, "Neck Rear Right Motor": 19}),
    ("Neck Rear Max",         {"Neck Rear Left Motor": "max", "Neck Rear Right Motor": "max"},   {"Neck Front Left Motor": 10, "Neck Front Right Motor": 10}),
    ("Neck Rear Left Min",    {"Neck Rear Left Motor": "min"},                                   {"Neck Rear Right Motor": 24, "Neck Front Left Motor": 24, "Neck Front Right Motor": 24}),
    ("Neck Rear Right Min",   {"Neck Rear Right Motor": "min"},                                  {"Neck Rear Left Motor": 24, "Neck Front Left Motor": 24, "Neck Front Right Motor": 24}),
    ("Head Yaw Max",          {"Head Yaw": "max"},                                               {}),
    ("Head Yaw Min",          {"Head Yaw": "min"},                                               {}),
]

## Full Size Tests

# |        Test          |  Dict of Controls                                                |    Positions for other controls    |
# |        Name          |  And which limit is tested ("min"/"max")                         |       If required for test         | 
FINGER_TESTS = [
    ("Fingers Max",           {"Index Finger Left": "max", "Index Finger Right": "max", "Little Finger Left": "max", "Little Finger Right": "max", "Middle Finger Left": "max", "Middle Finger Right": "max", "Ring Finger Left": "max", "Ring Finger Right": "max"}, {}),
    ("Fingers Min",           {"Index Finger Left": "min", "Index Finger Right": "min", "Little Finger Left": "min", "Little Finger Right": "min", "Middle Finger Left": "min", "Middle Finger Right": "min", "Ring Finger Left": "min", "Ring Finger Right": "min"}, {}),
]

FOREARM_TESTS = [
    ("Wrist Side Motors Max", {"Wrist Left Inner Motor": "max", "Wrist Right Inner Motor": "max", "Wrist Left Outer Motor": "max", "Wrist Right Outer Motor": "max" }, {}),
    ("Wrist Side Motors Min", {"Wrist Left Inner Motor": "min", "Wrist Right Inner Motor": "min", "Wrist Left Outer Motor": "min", "Wrist Right Outer Motor": "min" }, {}),
    ("Wrist Yaw Max",         {"Wrist Yaw Left": "max", "Wrist Yaw Right": "max"},              {}),
    ("Wrist Yaw Min",         {"Wrist Yaw Left": "min", "Wrist Yaw Right": "min"},              {}),
    ("Elbow Pitch Max",       {"Elbow Pitch Left": "max", "Elbow Pitch Right": "max"},          {}),
    ("Elbow Pitch Min",       {"Elbow Pitch Left": "min", "Elbow Pitch Right": "min"},          {}),
]

SHOULDER_TESTS = [
    ("Clavicle Roll Max",     {"Clavicle Roll Left": "max", "Clavicle Roll Right": "max"},      {}),
    ("Clavicle Roll Min",     {"Clavicle Roll Left": "min", "Clavicle Roll Right": "min"},      {}),
    ("Clavicle Yaw Max",      {"Clavicle Yaw Left": "max", "Clavicle Yaw Right": "max"},        {}),
    ("Clavicle Yaw Min",      {"Clavicle Yaw Left": "min", "Clavicle Yaw Right": "min"},        {}),
    ("Shoulder Pitch Max",    {"Shoulder Pitch Left": "max", "Shoulder Pitch Right": "max"},    {}),
    ("Shoulder Pitch Min",    {"Shoulder Pitch Left": "min", "Shoulder Pitch Right": "min"},    {}), 
    ("Shoulder Roll Max",     {"Shoulder Roll Left": "max", "Shoulder Roll Right": "max"},      {}),
    ("Shoulder Roll Min",     {"Shoulder Roll Left": "min", "Shoulder Roll Right": "min"},      {"Elbow Pitch Left": 40, "Elbow Pitch Right": 40}),
    ("Shoulder Yaw Max",      {"Shoulder Yaw Left": "max", "Shoulder Yaw Right": "max"},        {}),
    ("Shoulder Yaw Min",      {"Shoulder Yaw Left": "min", "Shoulder Yaw Right": "min"},        {}),    
]

TORSO_TESTS = [
    ("Torso Side Motors Max", {"Torso Left Motor": "max", "Torso Right Motor": "max"},          {}),
    ("Torso Side Motors Min", {"Torso Left Motor": "min", "Torso Right Motor": "min"},          {}),    
    ("Torso Yaw Max",         {"Torso Yaw": "max"},                                             {}),
    ("Torso Yaw Min",         {"Torso Yaw": "min"},                                             {}),
]


# Workaround for controls that cannot reach their actual limits Lip Bottom Curl. It cannot reach its min limit due to lip limiter script. We are instead overriding its limit

# |     Control                |  Limit  |   Overriden   |
# |      Name                  |  Type   |     Value     | 
LIMIT_OVERRIDES = {
    "Lip Bottom Curl":          {"min":       0.1}, # Cannot reach limit due to lip limiter script
    "Torso Left Motor":         {"min":       15,  # Physically cannot reach the torso limits
                                 "max":       42},
    "Torso Right Motor":        {"min":       15,
                                 "max":       42},
    "Wrist Left Inner Motor":   {"max":       27}, # Physically cannot reach the wrist max limits
    "Wrist Right Inner Motor":  {"max":       27},
    "Wrist Left Outer Motor":   {"max":       27},
    "Wrist Right Outer Motor":  {"max":       27},
}
# fmt: on

JOINT_CONTROLS = COMMON_JOINT_CONTROLS
DIFFERENTIAL_MODE_CONTROLS = COMMON_DIFFERENTIAL_MODE_CONTROLS

# Tests can contain test tuples or strings. if it is a string, the robot will say that text and wait WAIT_AFTER_TTS_S seconds
COMMON_TESTS = [
    *EYELID_TESTS,
    *EYE_TESTS,
    *BROW_TESTS,
    *NOSE_TESTS,
    *JAW_TESTS,
    *LIP_TESTS,
    *NECK_TESTS,
]

FULL_SIZE_TESTS = [
    *FINGER_TESTS,
    "Warning, starting to test the arms",
    *SHOULDER_TESTS,
    *FOREARM_TESTS,
    *TORSO_TESTS,
]

TESTS = COMMON_TESTS

if FULL_SIZE:
    JOINT_CONTROLS += FULL_SIZE_ONLY_JOINT_CONTROLS
    DIFFERENTIAL_MODE_CONTROLS += FULL_SIZE_ONLY_DIFFERENTIAL_MODE_CONTROLS
    TESTS += FULL_SIZE_TESTS

ctrls = {
    c: system.control(c, n, PARAMS_TO_ACQUIRE) for c, n, _, _, _, _ in JOINT_CONTROLS
}

ctrls_params = {
    c: {
        "default_position": default_position,
        "min_pos_current_limit": min_pos_current_limit,
        "max_pos_current_limit": max_pos_current_limit,
        "position_threshold": position_threshold,
    }
    for c, _, default_position, min_pos_current_limit, max_pos_current_limit, position_threshold in JOINT_CONTROLS
}

# Required to avoid limiting the Lip Bottom Depress Middle and Lip Top Raise Middle
# More details in on_start
jaw_pitch_control = system.control("Jaw Pitch", None, [])

diff_mode_ctrls = {
    c: system.control(c, n, []) for c, n, _ in DIFFERENTIAL_MODE_CONTROLS
}

diff_mode_ctrls_defaults = {
    c: diff_mode for c, _, diff_mode in DIFFERENTIAL_MODE_CONTROLS
}


async def start_and_stop_other_scripts():
    """
    Starts scripts that are required, stops scripts that can interfere with testing
    """
    # Stop other scripts that can interfere with testing
    for activity in system.unstable.state_engine._state.activities:
        if activity.get_property("script") in SCRIPTS_TO_STOP:
            system.unstable.state_engine.stop_activity(
                f"stopped by script: {system._path!r}", activity
            )

    # Need to wait for a bit, stopping HB3 stops do TTS, without a wait there is a race condition
    await asyncio.sleep(0.5)
    # Start scripts that are required:
    for script_path in SCRIPTS_TO_START:
        system.unstable.state_engine.start_activity(
            cause=f"started by script: {system._path!r}",
            activity_class="script",
            properties={
                "script": script_path,
                "script_file_path": f"/var/opt/tritium/scripts/{script_path}",
            },
        )


def get_tests():
    if TEST_OVERRIDE is not None:
        for test in TESTS:
            if test[0] == TEST_OVERRIDE:
                yield test
                return
        log.error(f"No test {TEST_OVERRIDE} found")
    else:
        yield from TESTS


class Activity:
    async def on_start(self):
        await start_and_stop_other_scripts()

        # Control positions might not be ready without this sleep
        # TODO: Investigate why
        await asyncio.sleep(0.1)

        # Lip Limiter limits Lip Bottom Depress Middle and Lip Top Raise Middle depending on Jaw Pitch
        # When we turn off differential mode, the Jaw Pitch position stops updating
        # Therefore we want to set the Jaw Pitch to open before toggling so it stops limiting the lip ranges
        # And we will manually ensure to only move them when jaw is open to prevent collisions
        jaw_pitch_control.demand = 0.65

        # switch to direct motor mode control for differential joints
        self.toggle_differential_mode(False)

        try:
            # Move to standard position
            await self.move_to_pose(self.default_position(), MOVE_TIME_S)

            # Start test
            for item in get_tests():
                if isinstance(item, str):
                    # The item is a string that the robot should say
                    if USE_TTS:
                        system.messaging.post("tts_say", [item, "EN"])
                        await asyncio.sleep(WAIT_AFTER_TTS_S)
                else:
                    # The item is a test definition
                    test_passed = True

                    test_name, tested_controls, other_control_positions = item
                    log.info(f"TEST {test_name} STARTED")

                    test_pose = self.default_position()

                    # Update the test control positions
                    for ctrl_name, limit in tested_controls.items():
                        test_pose[ctrl_name] = self.get_control_limit(ctrl_name, limit)

                    # Update the other control positions required by test
                    for ctrl_name, position in other_control_positions.items():
                        test_pose[ctrl_name] = position

                    # Move to test position
                    await self.move_to_pose(test_pose, MOVE_TIME_S)

                    await asyncio.sleep(HOLD_BEFORE_TEST_TIME_S)

                    # Hold and test, keep issuing demands to prevent fatigue
                    frames = int(TEST_TIME_S * TEST_FPS)

                    # Use averaged current and position rather than instants, otherwise can get a bit noisy
                    current_measurements = {}
                    position_measurements = {}
                    for ctrl_name in tested_controls.keys():
                        current_measurements[ctrl_name] = []
                        position_measurements[ctrl_name] = []

                    for i in range(frames):
                        self.demand_pose(test_pose)

                        await asyncio.sleep(TEST_SLEEP_TIME_S)

                        for ctrl_name in tested_controls.keys():

                            current_measurements[ctrl_name].append(
                                ctrls[ctrl_name].current
                            )
                            position_measurements[ctrl_name].append(
                                ctrls[ctrl_name].position
                            )

                    # Check Current
                    for (
                        ctrl_name,
                        current_measurements_list,
                    ) in current_measurements.items():
                        avg_current = sum(current_measurements_list) / len(
                            current_measurements_list
                        )

                        limit_type = tested_controls[ctrl_name]
                        if limit_type == "min":
                            current_limit = ctrls_params[ctrl_name][
                                "min_pos_current_limit"
                            ]
                        else:
                            current_limit = ctrls_params[ctrl_name][
                                "max_pos_current_limit"
                            ]

                        if avg_current > current_limit:
                            log.error(
                                f"TEST {test_name} FAILED: Control {ctrl_name} Current ({avg_current}) Over Limit ({current_limit}) "
                            )
                            if USE_TTS:
                                system.messaging.post(
                                    "tts_say",
                                    [
                                        f"Test {test_name} failed, {ctrl_name} current over limit",
                                        "EN",
                                    ],
                                )

                            test_passed = False
                        if VERBOSE:
                            log.info(
                                f"{ctrl_name} Current: {avg_current} limit: {current_limit}"
                            )

                    # Check Position
                    for (
                        ctrl_name,
                        position_measurements_list,
                    ) in position_measurements.items():
                        avg_position = sum(position_measurements_list) / len(
                            position_measurements_list
                        )
                        threshold = ctrls_params[ctrl_name]["position_threshold"]
                        min_limit = test_pose[ctrl_name] - threshold
                        max_limit = test_pose[ctrl_name] + threshold

                        if avg_position < min_limit or avg_position > max_limit:
                            log.error(
                                f"TEST {test_name} FAILED: Control {ctrl_name} Avg Position ({avg_position}) Not in Expected Range ({test_pose[ctrl_name]}±{threshold})"
                            )
                            if USE_TTS:
                                system.messaging.post(
                                    "tts_say",
                                    [
                                        f"Test {test_name} failed, {ctrl_name} position not within threshold",
                                        "EN",
                                    ],
                                )

                            test_passed = False
                        if VERBOSE:
                            log.info(
                                f"{ctrl_name} Position: {avg_position} limit: {test_pose[ctrl_name]} ± {threshold}"
                            )

                    if test_passed:
                        log.info(f"TEST {test_name} PASSED")
                    else:
                        log.warning(f"TEST {test_name} FAILED")

                    await self.move_to_pose(self.default_position(), MOVE_TIME_S)
            if USE_TTS:
                system.messaging.post("tts_say", ["Test Finished", "EN"])
        except Exception:
            log.exception("Exception during joint test")
            if USE_TTS:
                system.messaging.post(
                    "tts_say", ["Test stopped due to exception", "EN"]
                )
        finally:
            self.stop()

    def on_stop(self):
        self.toggle_differential_mode(True)

    def toggle_differential_mode(self, differential_mode: bool):
        for ctrl_name, ctrl in diff_mode_ctrls.items():
            if differential_mode:
                ctrl.mode = diff_mode_ctrls_defaults[ctrl_name]
            else:
                ctrl.mode = 0

    async def move_to_pose(self, to_pose, duration) -> list[dict[str, float]]:
        frames = int(duration * MOVE_FPS)
        from_pose = self.current_pose()
        for i in range(frames):
            for key, value_to in to_pose.items():
                demand = (value_to - from_pose[key]) * (i + 1) / frames + from_pose[key]
                try:
                    ctrls[key].demand = demand
                except ControlPropertyNotFoundError:
                    ctrls[key].demand_motor = demand
            await asyncio.sleep(MOVE_SLEEP_TIME_S)

    def demand_pose(self, pose):
        # Sends demand to all controls in pose. Used to keep sending demand while holding position to prevent fatigue
        for ctrl_name, value in pose.items():
            try:
                ctrls[ctrl_name].demand = value
            except ControlPropertyNotFoundError:
                ctrls[ctrl_name].demand_motor = value

    def current_pose(self) -> dict[str, float]:
        return {ctrl_name: ctrl.position for ctrl_name, ctrl in ctrls.items()}

    def default_position(self) -> dict[str, float]:
        return {
            ctrl_name: params["default_position"]
            for ctrl_name, params in ctrls_params.items()
        }

    def get_control_limit(self, ctrl_name: str, limit: str) -> float:
        if ctrl_name in LIMIT_OVERRIDES and limit in LIMIT_OVERRIDES[ctrl_name]:
            return LIMIT_OVERRIDES[ctrl_name][limit]

        ctrl = ctrls[ctrl_name]

        if limit == "min":
            return ctrl.min
        elif limit == "max":
            return ctrl.max
        else:
            raise ValueError(f"Unrecognized limit identifier: {limit}")