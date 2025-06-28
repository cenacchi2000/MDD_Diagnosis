"""
 This script is used to calibrate the joint encoder offsets (PWM) on the robots. 
 The calibration is necessary to do when a new module is made or the PWM encoder/magnet has changed on the robot.

 Updates:
     0.1.0: * Added Version.
            * Modified Shoulder Calibration: Clavicle Roll needs now a spacer as the end-stop is not very precise. 
                                             Also added a slight offset to previous calibration to robot limits match the CAD limits.
                                             See more on wiki.
     0.2.0: * Added Mitch leg parameters
            * Added firmware type option to deal with the different layout of parameters on BLDC boards
"""

version = "0.2.0"

import math
import asyncio
from time import time


class ParameterHandler:
    _requested_params = []

    def __init__(self):
        devices = system.unstable.owner.device_manager.devices
        params_by_name = {}

        for d in devices:
            for p in d.parameters:
                # print(vars(p))
                fqpn = "{}.{}".format(d.logical_name, p.name)
                fqpn2 = "{}.{}".format(d.logical_name, p.name_in_device_class)
                # print(p.name_in_device_class)
                # print(fqpn)
                # break
                params_by_name[fqpn] = p
                params_by_name[fqpn2] = p
        self.params_by_name = params_by_name
        self.params_by_ = params_by_name

    def deinit(self):
        for p in self._requested_params:
            self.drop_param(p)

    def set_param(self, param, demand):
        self.params_by_name[param].demand = demand

    def get_param(self, param):
        return self.params_by_name[param].value

    def request_param(self, param):
        p = self.params_by_name[param]
        system.unstable.owner.device_manager.acquire_parameters([p])
        self._requested_params.append(param)

    def drop_param(self, param):
        p = self.params_by_name[param]
        system.unstable.owner.device_manager.release_parameters([p])
        self._requested_params.remove(param)

    def requested_params(self):
        return self._requested_params


class Activity:
    board_names = []

    PHASES = [
        "request",
        "reset_offset",
        "set_offset",
        "two_point_calibration",
        "save_offset",
    ]

    def shoulder_function(self, value):
        a = 30
        b = 45
        theta1 = value * math.pi / 180
        theta2 = 2 * math.asin(
            b * math.sin(theta1) / math.sqrt(a**2 + b**2 + 2 * a * b * math.cos(theta1))
        )

        if theta1 > 2.30051849:
            theta2 = 2 * math.pi - theta2

        return theta2 * 180 / math.pi

    def find_shoulder_offset(self, value, expected):
        offset = 360
        while offset > -360:
            if value + offset < 360 and value + offset > 0:
                calculated = self.shoulder_function(value + offset)
                # print(f"{value} + {offset} =  {value + offset} -> {calculated}")
                error = calculated - expected
                if abs(error) < 0.1:
                    return offset
            offset -= 0.05

    async def do_calibration(self, phase):
        channels = {
            # Mesmer Shoulder Module D6
            # https://george.earts.dev/wiki/index.php/Mesmer_Shoulder_Module_-_D6
            ## Right
            ### Note: Shoulder Roll with amended end stop at 0 degrees (previous -10 degrees)
            #'Clavicle and Shoulder Right Motor Board.Shoulder Roll Right': {'scalar': 0.087890625,'value': 38.0, 'enabled': True, 'pwm_offset_center': 2048},   # All the way down
            ###With Spacer### 'Clavicle and Shoulder Right Motor Board.Shoulder Roll Right': {'scalar': 0.087890625,'value': 67.15, 'enabled': True, 'pwm_offset_center': 2048},   # 20mm spacer
            #'Clavicle and Shoulder Right Motor Board.Clavicle Roll Right': {'scalar': -0.087890625,'value': 80.465, 'enabled': True, 'pwm_offset_center': 2048},  # 20mm spacer
            #'Clavicle and Shoulder Right Motor Board.Clavicle Yaw Right':  {'scalar': 0.087890625,'value': -10.0, 'enabled': True, 'pwm_offset_center': 2048},    # All the way back
            ###With Spacer### 'Clavicle and Shoulder Right Motor Board.Clavicle Yaw Right':  {'scalar': 0.087890625,'value': 18.6, 'enabled': True, 'pwm_offset_center': 2048},    # 20mm spacer
            #'Clavicle and Shoulder Right Motor Board.Shoulder Yaw Right': {'scalar': 0.087890625,'value': -60.3,'enabled': True,'pwm_offset_center': 2048,},  # All the way back
            ## Left
            ### Note: Shoulder Roll with amended end stop at 0 degrees (previous -10 degrees)
            #'Clavicle and Shoulder Left Motor Board.Shoulder Roll Left': {'scalar': -0.087890625,'value': 38.0, 'enabled': True, 'pwm_offset_center': 2048},  # All the way down
            ###With Spacer### 'Clavicle and Shoulder Left Motor Board.Shoulder Roll Left': {'scalar': -0.087890625,'value': 67.15, 'enabled': True, 'pwm_offset_center': 2048},  # 20mm spacer
            #'Clavicle and Shoulder Left Motor Board.Clavicle Roll Left': {'scalar': 0.087890625,'value': 80.465, 'enabled': True, 'pwm_offset_center': 2048},   # 20mm spacer
            #'Clavicle and Shoulder Left Motor Board.Clavicle Yaw Left':  {'scalar': -0.087890625,'value': -10.0, 'enabled': True, 'pwm_offset_center': 2048},   # All the way back
            ###With Spacer### 'Clavicle and Shoulder Left Motor Board.Clavicle Yaw Left':  {'scalar': -0.087890625,'value': 18.6, 'enabled': True, 'pwm_offset_center': 2048},   # 20mm spacer
            #'Clavicle and Shoulder Left Motor Board.Shoulder Yaw Left':  {'scalar': -0.087890625,'value': -60.3, 'enabled': True, 'pwm_offset_center': 2048},  # All the way back
            ##### Mesmer Humerus Module v4 #####
            # https://george.earts.dev/wiki/index.php/Mesmer_Humerus_Module_-_v4
            ### Elbow Pitch: NO spacer used, arm needs to be straight (0degree on elbow) ###
            #'Arm Humerus Right Motor Board.Elbow Pitch Right':  {'scalar': 0.087890625,'value': 43.0, 'enabled': True, 'pwm_offset_center': 2048}, #  No spacer - arm is straight
            #'Arm Humerus Right Motor Board.Shoulder Pitch Right':  {'scalar': -0.087890625,'value': 132.2, 'enabled': True, 'offset_function': 'find_shoulder_offset', 'pwm_offset_center': 2048},  # 20mm spacer
            ### Elbow Pitch: NO spacer used, arm needs to be straight (0degree on elbow) ###
            #'Arm Humerus Left Motor Board.Elbow Pitch Left':  {'scalar': -0.087890625,'value': 43.0, 'enabled': True, 'pwm_offset_center': 2048},  # No spacer - arm is straight
            #'Arm Humerus Left Motor Board.Shoulder Pitch Left':  {'scalar': 0.087890625,'value': 132.2, 'enabled': True, 'offset_function': 'find_shoulder_offset', 'pwm_offset_center': 2048},  # 20mm spacer
            ##### Wrist #####
            # https://george.earts.dev/wiki/index.php/Wrist_Kinematics
            # Update firmware if possible and
            # Use this with firmware > v1.67.2  and make sure "High Level.Four Axis.Wrist Pitch.Offset" = 0
            #'Wrist Right Motor Board.Wrist Inner Motor':  {'scalar': -0.087890625,'value': -15.9, 'enabled': True, 'pwm_offset_center': 2048, 'high_level_offset_clear': True}, # 20mm spacer
            #'Wrist Right Motor Board.Wrist Outer Motor':  {'scalar': -0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048, 'high_level_offset_clear': True},   # 20mm spacer
            #'Wrist Left Motor Board.Wrist Inner Motor':  {'scalar': 0.087890625,'value': -15.9, 'enabled': True, 'pwm_offset_center': 2048, 'high_level_offset_clear': True},  # 20mm spacer
            #'Wrist Left Motor Board.Wrist Outer Motor':  {'scalar': 0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048, 'high_level_offset_clear': True},    # 20mm spacer
            # Use this with firmware version < v1.67.2  make sure "High Level.Four Axis.Wrist Pitch.Offset" = -8
            #'Wrist Right Motor Board.Wrist Inner Motor':  {'scalar': -0.087890625,'value': -23.9, 'enabled': True, 'pwm_offset_center': 2048}, # 20mm spacer
            #'Wrist Right Motor Board.Wrist Outer Motor':  {'scalar': -0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048},   # 20mm spacer
            #'Wrist Left Motor Board.Wrist Inner Motor':  {'scalar': 0.087890625,'value': -23.9, 'enabled': True, 'pwm_offset_center': 2048},  # 20mm spacer
            #'Wrist Left Motor Board.Wrist Outer Motor':  {'scalar': 0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048},    # 20mm spacer
            ##### Mesmer Neck v5 #####
            # https://george.earts.dev/wiki/index.php/Mesmer_Neck_V5_Kinematics
            #'Neck Motor Board.AE link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},  # 33mm spacer
            #'Neck Motor Board.BF link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},  # 33mm spacer
            #'Neck Motor Board.CG link':  {'scalar': -0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048}, # 19.1mm spacer
            #'Neck Motor Board.DH link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},  # 19.1mm spacer
            ##### Mesmer Neck v5 calibration stand #####
            # https://george.earts.dev/wiki/index.php/Mesmer_Neck_V5_Kinematics
            #'Neck Motor Board.AE link':  {'scalar': 0.087890625,'value': 22.68, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            #'Neck Motor Board.BF link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            #'Neck Motor Board.CG link':  {'scalar': -0.087890625,'value': -22.68, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            #'Neck Motor Board.DH link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            ##### Mesmer Neck v6 #####
            # https://george.earts.dev/wiki/index.php/Mesmer_Neck_6_Kinematics
            #'Neck Motor Board.AE link':  {'scalar': 0.087890625,'value': 20, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            #'Neck Motor Board.BF link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            #'Neck Motor Board.CG link':  {'scalar': -0.087890625,'value': -20, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            #'Neck Motor Board.DH link':  {'scalar': 0.087890625,'value': 0, 'enabled': True, 'sensor_post_process': 2, 'pwm_offset_center': 2048},
            ##### Mesmer Abdomen 2 #####
            # https://george.earts.dev/wiki/index.php/Mesmer_Abdomen_2#Kinematics
            #'Torso Motor Board.Torso Right Motor':  {'scalar': -0.087890625,'value': 8.7, 'enabled': True, 'pwm_offset_center': 2048}, # 20mm spacer #was 8.7 but leaning backwards at 0!
            #'Torso Motor Board.Torso Left Motor':  {'scalar': 0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048},   # 20mm spacer
            # Mesmer Abdomen 2 Calibration Stand
            # https://george.earts.dev/wiki/index.php/Mesmer_Abdomen_2#Kinematics
            #'Torso Motor Board.Torso Right Motor':  {'scalar': -0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048},
            #'Torso Motor Board.Torso Left Motor':  {'scalar': 0.087890625,'value': 0.0, 'enabled': True, 'pwm_offset_center': 2048},
            ### Two point calibration for Torso yaw: the motor will try to move from endstop to endstop ###
            # The encoder scaling can vary due to magnet strength/mechanical tolerances, so we need to calibrate the scaling too.
            #'Torso Motor Board.Torso Yaw':  {'type': 'two_point_calibration', 'range': 40, 'demand_duty': 10},
            ##### Mesmer Head V3 (Ameca G2 head) #####
            # https://https://george.earts.dev/wiki/index.php/Mesmer_Module_-_Skull_3
            #'Head Yaw Jaw and Nose Motor Board.Head Yaw':  {'scalar': 0.0879,'value': 45.0, 'enabled': True, 'pwm_offset_center': 2048}, # Move all the way to the left(Robots Left)
            ##### Mitch Left Leg #####
            # whole body leaning all the way to the left (right foot up off the floor)
            #'DRVD - Left Leg.Sensors.Encoder Roll': {'scalar': 0.087890625, 'value': -12.0, 'enabled': True, 'pwm_offset_center': 2048, 'firmware': 'bldc'},
            # head leaning all the way forward (bowing pose)
            #'DRVD - Left Leg.Sensors.Encoder Pitch': {'scalar': 0.087890625, 'value': 17.0, 'enabled': True, 'pwm_offset_center': 2048, 'firmware': 'bldc'}
        }

        request_params = [
            "Sensors.Encoder PWM.Raw",
            "Sensors.Encoder PWM.Offset",
            "Sensors.Encoder PWM.Polynome Coefficients",
            "Sensors.Encoder SSI",
        ]

        request_params_bldc = ["Raw", "Offset Raw", "Scalar", "Offset"]

        for c in channels:
            chan = channels[c]
            enabled = chan.get("enabled", True)
            value = chan.get("value", None)
            scalar = chan.get("scalar", None)
            type = chan.get("type", "one_point_calibration")
            firmware = chan.get("firmware", "bdc")
            # used for wrist pitch
            high_level_offset_clear = chan.get("high_level_offset_clear", False)

            if enabled:
                if phase == "two_point_calibration" and type == "two_point_calibration":
                    await self.two_way_calibration(
                        c, range=chan["range"], demand_duty=chan["demand_duty"]
                    )

                if phase == "request":
                    if firmware == "bdc":
                        plist = request_params
                    elif firmware == "bldc":
                        plist = request_params_bldc
                    for p in plist:
                        p_name = "{}.{}".format(c, p)
                        self.paramHandler.request_param(p_name)
                        print("Request: {}".format(p_name))

                if phase == "reset_offset":
                    # Set sensor post processing enum
                    if "sensor_post_process" in chan:
                        p_set = "{}.{}".format(
                            c, "Sensors.Encoder PWM.Sensor Post Processing"
                        )
                        self.paramHandler.set_param(p_set, chan["sensor_post_process"])

                    if "pwm_offset_center" in chan:
                        if firmware == "bdc":
                            p_get = "{}.{}".format(c, "Sensors.Encoder PWM.Raw")
                        else:
                            p_get = "{}.{}".format(c, "Raw")
                        raw = self.paramHandler.get_param(p_get)

                        o = chan["pwm_offset_center"] - raw
                        if firmware == "bdc":
                            p_set = "{}.{}".format(c, "Sensors.Encoder PWM.Offset")
                        else:
                            p_set = "{}.{}".format(c, "Offset Raw")
                        self.paramHandler.set_param(p_set, o)

                        if firmware == "bdc":
                            p_set = "{}.{}".format(
                                c, "Sensors.Encoder PWM.Polynome Coefficients"
                            )
                            self.paramHandler.set_param(p_set, [0, 0, 0, scalar, 0])
                        else:
                            p_set = "{}.{}".format(c, "Scalar")
                            self.paramHandler.set_param(p_set, scalar)

                        if firmware == "bdc":
                            p_set = "{}.{}".format(c, "Sensors.Encoder PWM.Gain")
                            self.paramHandler.set_param(p_set, 1)

                if phase == "set_offset":
                    # use this for PWM type encoders
                    if "pwm_offset_center" in chan:
                        if firmware == "bdc":
                            p_get = "{}.{}".format(c, "Sensors.Encoder PWM.Raw")
                        else:
                            p_get = "{}.{}".format(c, "Raw")
                        raw = self.paramHandler.get_param(p_get)

                        if firmware == "bdc":
                            p_get = "{}.{}".format(c, "Sensors.Encoder PWM.Offset")
                        else:
                            p_get = "{}.{}".format(c, "Offset Raw")
                        offset = self.paramHandler.get_param(p_get)

                        scaled = (raw + offset) % 4096
                        print(raw + offset)
                        print(scaled * scalar)
                        if "offset_function" in chan:
                            my_func = getattr(self, chan["offset_function"])
                            constant = my_func(scaled * scalar, value)
                        else:
                            constant = value - scaled * scalar

                        if firmware == "bdc":
                            p_set = "{}.{}".format(
                                c, "Sensors.Encoder PWM.Polynome Coefficients"
                            )
                            self.paramHandler.set_param(
                                p_set, [0, 0, 0, scalar, constant]
                            )
                        else:
                            p_set = "{}.{}".format(c, "Offset")
                            self.paramHandler.set_param(p_set, constant)

                    # only the Torso Yaw at the moment
                    if "set_position_control_offset" in chan:
                        p_set = "{}.{}".format(
                            c, "Controller - Position Parameters.Encoder Scalar"
                        )
                        self.paramHandler.set_param(p_set, chan["scalar"])

                        p_get = "{}.{}".format(c, "Sensors.Encoder SSI")
                        ssi_value = self.paramHandler.get_param(p_get)

                        offset = 0 - ssi_value * chan["scalar"]
                        p_set = "{}.{}".format(
                            c, "Controller - Position Parameters.Encoder Offset"
                        )
                        self.paramHandler.set_param(p_set, offset)

                    if high_level_offset_clear == True:
                        dev = c.split(".")[0]
                        self.paramHandler.set_param(
                            f"{dev}.High Level.Four Axis.Axis1.Offset", 0
                        )

        if phase == "save_offset":
            devices_to_save = set()
            for c in channels:
                dev = c.split(".")[0]
                devices_to_save.add(dev)
            print("Save persistent data for devices", devices_to_save)
            for d in devices_to_save:
                device = system.unstable.owner.device_manager.get_device_by_name(d)
                for dh in system.unstable.owner.device_manager.device_hosts:
                    if device in dh.devices:
                        host = dh
                await host.client.call_api("save_parameters", deviceID=device.id)

    # Only Torso Yaw at the moment
    async def two_way_calibration(self, ch, range, demand_duty):
        p_name = f"{ch}.Sensors.Encoder PWM.Raw"
        self.paramHandler.request_param(p_name)
        print(f"Request: {p_name}")
        await asyncio.sleep(0.5)

        # Set to direct mode
        self.paramHandler.set_param(f"{ch}.Config.Control Mode", 0)
        self.paramHandler.set_param(f"{ch}.Config.Enable", True)
        self.paramHandler.set_param(f"{ch}.Config.Output Enable", True)

        async def drive_to_end(duty):
            self.paramHandler.set_param(f"{ch}.Demands.Duty Cycle", duty)
            raw_prev = 0
            start_time = time()
            while True:
                raw = self.paramHandler.get_param(f"{ch}.Sensors.Encoder PWM.Raw")
                diff = abs(raw_prev - raw)
                # Check if we hit the endstop
                if diff < 2 and now - start_time > 10:
                    self.paramHandler.set_param(f"{ch}.Demands.Duty Cycle", 0)
                    return True

                # 15 sec timeout if we never reach endstop
                now = time()
                if now - start_time > 30:
                    self.paramHandler.set_param(f"{ch}.Demands.Duty Cycle", 0)
                    return False

                # print(diff)
                raw_prev = raw
                await asyncio.sleep(0.2)

        success = await drive_to_end(demand_duty)
        if success:
            hardstop1 = self.paramHandler.get_param(f"{ch}.Sensors.Encoder PWM.Raw")
            success = await drive_to_end(-demand_duty)
            if success:
                hardstop2 = self.paramHandler.get_param(f"{ch}.Sensors.Encoder PWM.Raw")
                try:
                    scalar = range / (hardstop1 - hardstop2)
                    offset = -(hardstop2 + ((hardstop1 - hardstop2) / 2)) * scalar
                    print(hardstop1, hardstop2, scalar, offset)

                    p_set = f"{ch}.Sensors.Encoder PWM.Offset"
                    self.paramHandler.set_param(p_set, 0)

                    p_set = f"{ch}.Sensors.Encoder PWM.Polynome Coefficients"
                    self.paramHandler.set_param(p_set, [0, 0, 0, scalar, offset])

                    self.paramHandler.set_param(f"{ch}.Config.Control Mode", 1)
                    self.paramHandler.set_param(
                        f"{ch}.Config.Clear Absolute Flag", True
                    )
                    await asyncio.sleep(0.5)
                    self.paramHandler.set_param(
                        f"{ch}.Config.Clear Absolute Flag", False
                    )
                    self.paramHandler.set_param(f"{ch}.Config.Enable", False)
                    await asyncio.sleep(0.5)
                    self.paramHandler.set_param(f"{ch}.Config.Enable", True)
                    await asyncio.sleep(0.5)
                    self.paramHandler.set_param(f"{ch}.Demands.Position", 0.1)
                    await asyncio.sleep(0.5)
                    self.paramHandler.set_param(f"{ch}.Demands.Position", 0.0)
                except ZeroDivisionError:
                    log.error(
                        "PWM Encoder value isn't changing! Please ensure the hardware is functioning nominally."
                    )
                    log.error(
                        f"Current Hardstop Values: [Hardstop1: {hardstop1}, Hardstop2: {hardstop2}]"
                    )
            else:
                print("Timeout never reached hardstop2")
        else:
            print("Timeout never reached hardstop1")

    def on_start(self):
        self.tick_count = 0
        self.paramHandler = ParameterHandler()
        self.devices = system.unstable.owner.device_manager.devices

    def on_stop(self):
        self.paramHandler.deinit()

    @system.tick(fps=100)
    async def on_tick(self):
        if self.tick_count == 0:
            await self.do_calibration(self.PHASES[0])

        if self.tick_count == 100:
            await self.do_calibration(self.PHASES[1])

        if self.tick_count == 200:
            await self.do_calibration(self.PHASES[2])

        if self.tick_count == 300:
            await self.do_calibration(self.PHASES[3])

        if self.tick_count == 400:
            await self.do_calibration(self.PHASES[4])

        if self.tick_count == 500:
            self.stop()

        for p in self.paramHandler.requested_params():
            probe(p, self.paramHandler.get_param(p))
        self.tick_count += 1
        probe("tick_count", self.tick_count)
