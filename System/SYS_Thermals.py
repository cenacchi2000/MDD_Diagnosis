"""
This system script monitors the temperature of the head and automatically adjusts the fan speed accordingly

Changes:
    0.0.1: Initial release for full size robot
    1.0.0: Modify it for desktop robots
    1.1.0: Tweak fan curves and smooth the response out
    1.2.0: Different fan curve for boards with internal MCU temp sensors
"""

from statistics import fmean

from ea.util.number import remap_keyframes

ctrls = {
    c: system.control(c, n, p)
    for c, n, p in [
        (
            "Head Fan",
            None,
            (
                "fan_duty_cycle",
                "lip_board_temp",
                "fan_tacho",
            ),
        ),
        ("Brows Temp", None, ("brows_board_temp",)),
        ("Eye Driver Temp", None, ("eye_driver_temp",)),
        ("Eye MCU Temp", None, ("eye_mcu_temp",)),
        ("Yaw Jaw Temp", None, ("yaw_jaw_board_temp",)),
    ]
}


class Activity:
    ## Head fan speeds and temps ##
    mcu_head_fan_curve = [(45, 0.2), (69, 0.45), (85, 0.95)]
    ext_head_fan_curve = [(35, 0.1), (60, 0.5), (63, 0.8)]
    head_history = []

    arbitration = {
        "controls": "Thermals",
        "precedence": Precedence.VERY_LOW,
        "type": BidType.EXCLUSIVE,
    }

    @system.tick(fps=3)
    def on_tick(self):
        ## Head Temps ##
        lip_temp = round(or_0(ctrls["Head Fan"].lip_board_temp), 2)
        brow_temp = round(or_0(ctrls["Brows Temp"].brows_board_temp), 2)
        eye_driver_temp = round(or_0(ctrls["Eye Driver Temp"].eye_driver_temp), 2)
        eye_mcu_temp = round(or_0(ctrls["Eye MCU Temp"].eye_mcu_temp), 2)
        yaw_jaw_temp = round(or_0(ctrls["Yaw Jaw Temp"].yaw_jaw_board_temp), 2)

        highest_mcu_head_temp = max(lip_temp, brow_temp)
        highest_ext_head_temp = max(eye_driver_temp, eye_mcu_temp, yaw_jaw_temp)

        self.set_fan_speed(
            max(
                remap_keyframes(highest_mcu_head_temp, self.mcu_head_fan_curve),
                remap_keyframes(highest_ext_head_temp, self.ext_head_fan_curve),
            ),
            "head",
        )

        # ...or you can watch any other value in the IDE for debugging
        probe("Head Fan Speed", 1 - or_1(ctrls["Head Fan"].fan_duty_cycle))
        probe("Head Fan Tacho", ctrls["Head Fan"].fan_tacho)
        probe("lip temp", f"{lip_temp} ℃")
        probe("brow temp", f"{brow_temp} ℃")
        probe("eye mcu temp", f"{eye_mcu_temp} ℃")
        probe("eye driver temp", f"{eye_driver_temp} ℃")
        probe("yaw jaw temp", f"{yaw_jaw_temp} ℃")
        probe("Highest MCU temp", f"{highest_mcu_head_temp} ℃")
        probe("Highest Ext temp", f"{highest_ext_head_temp} ℃")

    def set_fan_speed(self, speed, fan):
        # V3 head 16ch board the fan output is inverted
        if fan == "head":
            ctrls["Head Fan"].fan_duty_cycle = 1 - roll(speed, self.head_history, 20)


def roll(value: float, history: list[float], count: int) -> float:
    history.append(value)
    if len(history) > count:
        history.pop(0)
    return fmean(history)


def or_0(val):
    if not val:
        return 0
    return val


def or_1(val):
    if val is None:
        return 1
    return val