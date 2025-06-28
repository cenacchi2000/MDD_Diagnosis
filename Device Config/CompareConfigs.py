import re
import json
import math

from ea.util.scheduler import Scheduler


class Activity:
    # Comment it if you want to overwrite valus not just to compare
    COMPARE_ONLY = True

    ########## COMPARE from a file ##########
    #     COMPARE = [
    #         {
    #             "input_file": "/var/opt/tritium/profile/nodes/proxy_device_host_usb/device_states/Hand Right Motor Board.json",
    #             "input_filter": "Channel 1.",
    #             "output_filters":
    #             [
    #                 "Hand Right Motor Board.Channel 2",
    #             ]
    #         }
    #     ]

    COMPARE = [
        ########## FINGERS ##########
        #         {
        #             "input_device": "Hand Right Motor Board",
        #             "input_filter": "Channel 1.",
        #             "ignore_params_extra":
        #             [
        #                 "Controller - Limits.Lower Limit",
        #                 "Controller - Limits.Upper Limit"
        #             ],
        #             "output_filters":
        #             [
        #                 "Hand Right Motor Board.Channel 2",
        #                 "Hand Right Motor Board.Channel 3",
        #                 "Hand Right Motor Board.Channel 4",
        #                 "Hand Left Motor Board.Channel 1",
        #                 "Hand Left Motor Board.Channel 2",
        #                 "Hand Left Motor Board.Channel 3",
        #                 "Hand Left Motor Board.Channel 4",
        #             ]
        #         },
        #         ########## WRISTS ##########
        #         # Wrist pitch and roll
        #         {
        #             "input_device": "Wrist Right Motor Board",
        #             "input_filter": "Channel 1",
        #             "output_filters":
        #             [
        #                 "Wrist Right Motor Board.Channel 2",
        #                 "Wrist Left Motor Board.Channel 1",
        #                 "Wrist Left Motor Board.Channel 2",
        #             ]
        #         },
        #         # Wrist yaw
        #         {
        #             "input_device": "Wrist Right Motor Board",
        #             "input_filter": "Channel 3",
        #             "output_filters":
        #             [
        #                 "Wrist Left Motor Board.Channel 3",
        #             ]
        #         },
        #         # Wrist high level
        #         {
        #             "input_device": "Wrist Right Motor Board",
        #             "input_filter": "High Level",
        #             "output_filters":
        #             [
        #                 "Wrist Left Motor Board.High Level",
        #             ]
        #         },
        #         ########## ARMS ##########
        #         # Elbow pitch
        #         {
        #             "input_device": "Arm Humerus Right Motor Board",
        #             "input_filter": "Channel 1",
        #             "output_filters":["Arm Humerus Left Motor Board.Channel 1",]
        #         },
        # Shoulder pitch
        {
            "input_device": "Arm Humerus Right Motor Board",
            "input_filter": "Channel 2",
            "output_filters": [
                "Arm Humerus Left Motor Board.Channel 2",
            ],
        },
        #         ########## SHOULDERS ##########
        #         {
        #             "input_device": "Clavicle and Shoulder Right Motor Board",
        #             "input_filter": "Channel 1",
        #             "output_filters": ["Clavicle and Shoulder Left Motor Board.Channel 1",]
        #         },
        #         {
        #             "input_device": "Clavicle and Shoulder Right Motor Board",
        #             "input_filter": "Channel 2",
        #             "output_filters": ["Clavicle and Shoulder Left Motor Board.Channel 2",]
        #         },
        #         {
        #             "input_device": "Clavicle and Shoulder Right Motor Board",
        #             "input_filter": "Channel 3",
        #             "output_filters": ["Clavicle and Shoulder Left Motor Board.Channel 3",]
        #         },
        #         {
        #             "input_device": "Clavicle and Shoulder Right Motor Board",
        #             "input_filter": "Channel 4",
        #             "output_filters": ["Clavicle and Shoulder Left Motor Board.Channel 4",]
        #         },
        #         ########## TORSO ##########
        #         {
        #             "input_device": "Torso Motor Board",
        #             "input_filter": "Channel 1",
        #             "output_filters": ["Torso Motor Board.Channel 2",]
        #         },
        #         ########## NECK ##########
        #         {
        #             "input_device": "Neck Motor Board",
        #             "input_filter": "Channel 1",
        #             "output_filters": [
        #                 "Neck Motor Board.Channel 2",
        #                 "Neck Motor Board.Channel 3",
        #                 "Neck Motor Board.Channel 4",
        #            ]
        #         },
        #         ########## LIPS V2 ##########
        #         {
        #             "input_device": "Lips Left and Bottom Motor Board",
        #             "input_filter": "Lip Bottom Curl",
        #             "output_filters": [
        #                 "Lips Right and Top Motor Board.Lip Top Curl",
        #            ]
        #         },
        #         {
        #             "input_device": "Lips Left and Bottom Motor Board",
        #             "input_filter": "Lip Corner Bottom Left Motor",
        #             "output_filters": [
        #                 "Lips Right and Top Motor Board.Lip Corner Bottom Right Motor",
        #            ]
        #         },
        #         {
        #             "input_device": "Lips Left and Bottom Motor Board",
        #             "input_filter": "Lip Corner Top Left Motor",
        #             "output_filters": [
        #                 "Lips Right and Top Motor Board.Lip Corner Top Right Motor",
        #            ]
        #         },
        #         ########## LIPS ##########
        #         {
        #             "input_device": "Lips Motor Board",
        #             "input_filter": "Lip Corner Right",
        #             "output_filters": [
        #                 "Lips Motor Board.Lip Corner Left",
        #            ]
        #         },
        #         ########## BROWS ##########
        #         {
        #             "input_device": "Brows Motor Board",
        #             "input_filter": "Brow Outer Right",
        #             "output_filters": ["Brows Motor Board.Brow Outer Left",]
        #         },
        #         {
        #             "input_device": "Brows Motor Board",
        #             "input_filter": "Brow Inner Right",
        #             "output_filters": ["Brows Motor Board.Brow Inner Left",]
        #         },
        #         ########## EYES, EYELIDS ##########
        #         {
        #             "input_device": "Eyeball Right Motor Board",
        #             "input_filter": "Eye Pitch Right",
        #             "ignore_params_extra": ["Demands.Position Offset",],
        #             "output_filters": ["Eyeball Left Motor Board.Eye Pitch Left",]
        #         },
        #         {
        #             "input_device": "Eyeball Right Motor Board",
        #             "input_filter": "Eye Yaw Right",
        #             "ignore_params_extra": ["Demands.Position Offset",],
        #             "output_filters": ["Eyeball Left Motor Board.Eye Yaw Left",]
        #         },
        #         {
        #             "input_device": "Eyeball Right Motor Board",
        #             "input_filter": "Top Lid Right",
        #             "ignore_params_extra":
        #             [
        #                 "Demands.Initial Position",
        #                 "Controller - Limits.Lower Limit",
        #                 "Controller - Limits.Upper Limit",
        #             ],
        #             "output_filters": [
        #                 "Eyeball Right Motor Board.Bottom Lid Right",
        #                 "Eyeball Left Motor Board.Top Lid Left",
        #                 "Eyeball Left Motor Board.Bottom Lid Left",
        #             ]
        #         },
        #         {
        #             "input_device": "Eyeball Right Motor Board",
        #             "input_filter": "Top Lid Right",
        #             "output_filters": ["Eyeball Left Motor Board.Top Lid Left",]
        #         },
        #         {
        #             "input_device": "Eyeball Right Motor Board",
        #             "input_filter": "Bottom Lid Right",
        #             "output_filters": ["Eyeball Left Motor Board.Bottom Lid Left",]
        #         },
        #         ######### JAWS ##########
        #         {
        #             "input_device": "Head Yaw and Jaw Motor Board",
        #             "input_filter": "Jaw Right",
        #             "output_filters": [
        #                 "Head Yaw and Jaw Motor Board.Jaw Left",
        #             ]
        #         }
    ]

    GLOBAL_IGNORE_PARAMS = [
        ".Output.Invert",
        #         ".Encoder SSI.Offset",
        ".Encoder SSI.Gain",
        ".Encoder SSI.Ignore Error Bit",
        ".Encoder PWM.Offset",
        ".Encoder PWM.Gain",
        ".Encoder PWM.Polynome Coefficients",
        # ".Setup Home Position Motion.",
        ".Position Parameters.Encoder Offset",
        ".Position Parameters.Encoder Scalar",
        ".Controller - Position Parameters.Encoder Offset",
    ]

    requested_params = []

    def is_ignored(self, pname, pname_in_device_class, ignore_params):
        for i in ignore_params:
            if i in pname or i in pname_in_device_class:
                return True
        return False

    def get_parameters_from_device(self, device, input_filter, ignore_params):
        parameters = []
        for dev in system.unstable.owner.device_manager.devices:
            if dev.identifier.startswith("proxy_device_host_usb_"):
                print(device, dev.logical_name)
                if device == dev.logical_name:
                    for p in dev.parameters:
                        if p.persistent:
                            # Check if we have to ignore parameter
                            if (
                                input_filter in p.name
                                or input_filter in p.name_in_device_class
                            ):
                                if not self.is_ignored(
                                    p.name, p.name_in_device_class, ignore_params
                                ):
                                    # Request paramater value
                                    if p not in self.requested_params:
                                        system.unstable.owner.device_manager.acquire_parameters(
                                            [p]
                                        )
                                        self.requested_params.append(p)

                                    o = {}
                                    o["parameter"] = p
                                    o["name"] = p.name
                                    o["name_in_device_class"] = p.name_in_device_class
                                    o["value"] = None

                                    parameters.append(o)

        return parameters

    def get_parameters_from_file(self, filename, input_filter, ignore_params):
        parameters = []
        with open(filename) as json_file:
            data = json.load(json_file)
            if "parameters" in data:
                data = data["parameters"]
                for p in data:
                    if (
                        input_filter in p["name"]
                        or input_filter in p["name_in_device_class"]
                    ):
                        if not self.is_ignored(
                            p["name"], p["name_in_device_class"], ignore_params
                        ):
                            parameters.append(p)
        return parameters

    def get_host_for_device(self, device):
        # Get the persistent
        for dev_host_name in self.robot.device_manager.device_hosts_by_name:
            h = self.robot.device_manager.device_hosts_by_name[dev_host_name]
            if device in h.devices:
                return h
        return None

    def save_parameters(self, device):
        print("Saving")
        host = self.get_host_for_device(device)

        def cb(error):
            if error:
                print(
                    "Failed to save parameters for {}: {}".format(
                        device.identifier, error
                    )
                )
            else:
                print("Parameters saved for {}".format(device.identifier))

        host.client.call_api(
            "save_parameters", callback=cb, expect_json=True, deviceID=device.id
        )

    def get_persistent_value(self, param):
        print(param)
        return 0
        # h = self.get_host_for_device(param._device)
        # filename = h.get_device_persistent_data_path(param._device)
        # with open(filename) as json_file:
        #     data = json.load(json_file)
        #     for p in data['parameters']:
        #         if (p['name_in_device_class'] == param.name or
        #            p['name_in_device_class'] == param.name_in_device_class or
        #            p['name'] == param.name or
        #            p['name'] == param.name_in_device_class):
        #             return p['value']

    def find_output_param(self, filter, pname, pnamedc):
        s = filter.split(".")
        out_dev = s[0]
        out_cat = s[1]
        devices = self.robot.device_manager.devices

        input_name = pname.split(".", 1)[1]
        input_namedc = pnamedc.split(".", 1)[1]

        for d in devices:
            if d.identifier == out_dev:
                for p in d.parameters:
                    # Split output inputs
                    s1 = p.name.split(".", 1)
                    s2 = p.name_in_device_class.split(".", 1)
                    c1 = s1[0]
                    c2 = s2[0]
                    # Check if catageory matches
                    if out_cat == c1 or out_cat == c2:
                        cp1 = s1[1]
                        cp2 = s2[1]
                        # Check if reset (subcategory.name) matches
                        if input_name == cp1 or input_name == cp2:
                            return p
                        if input_namedc == cp1 or input_namedc == cp2:
                            return p
        return None

    def copy_params(self, input_params, output_filters, compare_only=True):
        updated_devices = []
        # Check if was successful
        if input_params is None:
            print("Cannot read input parameters.")
            self.stop()

        for f in output_filters:
            changed_param_cntr = 0
            # print("\n\nDifferent params {}:".format(f))

            for p in input_params:
                pnamedc = p["name_in_device_class"]
                pname = p["name"]
                pvalue_new = p["value"]
                if pvalue_new is None:
                    pp = p["parameter"]
                    a = pp.value
                    pvalue_new = a

                # Check if we can find a paramater to match our input param
                param_to_set = self.find_output_param(f, pname, pnamedc)

                # A matching param has been found
                if param_to_set:
                    # Get the current persistent value of the parmater
                    pv = self.get_persistent_value(param_to_set)
                    # Check if the parameters current value equals to the input param's value
                    if pv != pvalue_new:
                        # Update the value
                        if param_to_set._device not in updated_devices:
                            # Make a note that this device is updated
                            updated_devices.append(param_to_set._device)

                        changed_param_cntr += 1
                        print(
                            "'{}': '{}' <-- '{}'".format(
                                param_to_set.name, pv, pvalue_new
                            )
                        )
                        # Compare only?
                        if not compare_only:
                            param_to_set.demand = pvalue_new
                            if param_to_set not in self.requested_params:
                                self.robot.device_manager.acquire_parameters(
                                    [param_to_set]
                                )
                                self.requested_params.append(param_to_set)

                    else:
                        # print("\n\n{}:\ncurrent == new:  {} == {}".format(param_to_set.name, pv, pvalue_new))
                        pass
            #             if changed_param_cntr == 0:
            #                 print("{}: 0 chabges".format(f))
            #             else:
            print("Changed params for '{}': {}\n".format(f, changed_param_cntr))

        if not compare_only:
            for d in updated_devices:
                self.scheduler.schedule(self.save_parameters, 1, device=d)

    def compare_params(self):
        for c in self.COMPARE:
            input_filter = c["input_filter"]
            output_filters = c["output_filters"]
            ignore_params = c.get("ignore_params", self.GLOBAL_IGNORE_PARAMS)
            ignore_params_extra = c.get("ignore_params_extra", [])
            ignore_params += ignore_params_extra

            if "input_file" in c:
                input_params = self.get_parameters_from_file(
                    c["input_file"], input_filter, ignore_params
                )
            else:
                input_params = self.get_parameters_from_device(
                    c["input_device"], input_filter, ignore_params
                )
            print(input_params)
            # schedule 1 sec ahead as if we read from input_device we need to wait until we get some params from tritium
            #             self.copy_params(input_params, output_filters, self.COMPARE_ONLY)
            self.scheduler.schedule(
                self.copy_params,
                1,
                input_params=input_params,
                output_filters=output_filters,
                compare_only=self.COMPARE_ONLY,
            )

        # i
        # self.copy_params(input_params, self.OUTPUT_CHANNELS, self.COMPARE_ONLY)

    def on_start(self):
        self.scheduler = Scheduler()
        self.tick_count = 0
        if not hasattr(self, "COMPARE_ONLY"):
            self.COMPARE_ONLY = False
        self.compare_params()

        # Stop after 2 sec
        self.scheduler.schedule(self.stop, 10)

    def on_stop(self):
        # self.robot.device_manager.release_parameters(self.requested_params)
        # self.requested_params = []
        pass

    @system.tick(fps=10)
    def on_tick(self):
        print("asd")
        self.scheduler.run()
        self.tick_count += 1
        self.stop()
        # self.set_debug_value('tick_count', self.tick_count)