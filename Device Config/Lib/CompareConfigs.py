"""
Add a short description of your script here

See https://tritiumrobot.cloud/docs/ for more information
"""


class CompareConfigs:
    GLOBAL_IGNORE_PARAMS = [
        ".Output.Invert",
        # ".Encoder SSI.Offset",
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

    def is_ignored(self, p, ignore_params):
        pname = p.get("name", "")
        pname_in_device_class = p.get("name_in_device_class", "")
        for i in ignore_params:
            if i in pname or i in pname_in_device_class:
                return True
        return False

    def compare_configs(
        self, config1, config2, ignore_filter=GLOBAL_IGNORE_PARAMS, verbose=True
    ):
        different_params = []
        for p1 in config1["device_states"]["parameters"]:
            p1name = p1.get("name", None)
            p1name_in_device_class = p1.get("name_in_device_class", None)
            p1value = p1.get("value", None)
            if not self.is_ignored(p1, ignore_filter):
                found = False
                idx = 0
                for p2 in config2["device_states"]["parameters"]:
                    p2name = p2.get("name", None)
                    p2name_in_device_class = p2.get("name_in_device_class", None)
                    p2value = p2.get("value", None)
                    if p1name_in_device_class is not None:
                        if (
                            p1name_in_device_class == p2name
                            or p1name_in_device_class == p2name_in_device_class
                        ):
                            found = True
                    elif p1name is not None:
                        if p1name == p2name or p1name == p2name_in_device_class:
                            found = True
                    if found:
                        if p1value != p2value:
                            config2["device_states"]["parameters"][idx][
                                "value"
                            ] = p1value
                            if verbose:
                                print(
                                    f"'{p1name_in_device_class}': (old)'{p2value}'  -->  (new)'{p1value}'"
                                )
                        break
                    else:
                        idx += 1
        return config2