"""
Set The LED Light Color
"""

import math
from time import monotonic
from typing import List, Optional

CONFIG = system.import_library("../../Config/HB3.py").CONFIG
ModeController = system.import_library("../chat/mode_controller.py").ModeController
is_other_script_running = system.import_library("../utils.py").is_other_script_running

ROBOT_STATE = system.import_library("../robot_state.py")
robot_state = ROBOT_STATE.state

LED_Keys: Optional[List[str]] = None
if CONFIG["LED_TYPE"] == CONFIG["LED_TYPES"].ADDRESSABLE_LEDs:
    LED_Keys = [
        "Front Left",
        "Front Right",
        "Middle Left",
        "Middle Right",
        "Rear Left",
        "Rear Right",
    ]
else:
    LED_Keys = ["All"]


DEFAULT_COLOR = (0.6, 0.6, 0.6)

# Usage status colors
TELEPRESENCE_COLOR = (0, 1, 1)
LIDAR_BREACHED_COLOR = (1, 0, 0)
PHOTO_MODE_COLOR = (0, 0.2, 1)

# Operational Mode colors
OPERATIONAL_MODE_COLORS = {
    "startup": (0.1, 0.5, 0.1),
    "active": DEFAULT_COLOR,
    "stopped": (1, 0, 0),
    "manual": (1, 0, 0),
}

# Chat Controller Mode colors
CHAT_MODE_COLORS = {
    "interaction": (1, 0, 1),
    "silent": (1, 1, 0),
    "conference": (0.4, 0, 0.8),  # TODO management decide on colour
    "customisation": (0, 0, 1),
}

# pulsing
MIN_INTENSITY = 0.1
MAX_INTENSITY = 1.0
PULSE_RATE = 1.5

# These controls are not required - so that we're compatible with robots without lidars
combined_lidar = system.control(
    "Combined Lidar", namespace=None, acquire=["ok"], required=False
)
left_lidar = system.control(
    "Left Lidar", namespace=None, acquire=["bypass"], required=False
)
right_lidar = system.control(
    "Right Lidar", namespace=None, acquire=["bypass"], required=False
)


class LED:
    def __init__(self, key):
        self.key = key
        self.r_ctrl = system.control(key + " LED Red", "Mesmer Head LEDs 1")
        self.g_ctrl = system.control(key + " LED Green", "Mesmer Head LEDs 1")
        self.b_ctrl = system.control(key + " LED Blue", "Mesmer Head LEDs 1")

    def set_rgb(self, r, g, b):
        self.r_ctrl.demand = r
        self.g_ctrl.demand = g
        self.b_ctrl.demand = b


control_keys = {key: LED(key) for key in LED_Keys}


class Activity:
    telepresence_running = False
    _current_color = DEFAULT_COLOR
    _previous_source = None
    _temporary_color = None
    _legacy_lidar_breached = False

    # pulsing effect for thinking
    stop_pulsing_requested = False
    is_pulsing = False
    pulse_start_time = None

    def _set_lights(self, r, g, b):
        for key in LED_Keys:
            control_keys[key].set_rgb(r, g, b)

    def on_message(self, channel, message):
        if channel == "set_led":
            self._temporary_color = message

        elif channel == "legacy_lidar":
            self._legacy_lidar_breached = message

        elif channel == "telepresence":
            if message.get("type", "") == "session_active":
                self.telepresence_running = message.get("value", False)

    def get_default_led_color(self):
        if self._legacy_lidar_breached:
            return "lidar_breached", LIDAR_BREACHED_COLOR

        if (
            not left_lidar.bypass
            and not right_lidar.bypass
            and combined_lidar.ok is False
        ):
            return "lidar_breached", LIDAR_BREACHED_COLOR

        if self.telepresence_running:
            return "telepresence", TELEPRESENCE_COLOR

        if robot_state.is_camera_tracking:
            return "photo mode", PHOTO_MODE_COLOR

        if is_other_script_running(system, "../Chat_Controller.py"):
            chat_mode = ModeController.get_current_mode_name()
            color = CHAT_MODE_COLORS.get(chat_mode, CHAT_MODE_COLORS["interaction"])
            return f"chat_{chat_mode}", color

        op_mode = system.unstable.state_engine.operational_mode_identifier
        color = OPERATIONAL_MODE_COLORS.get(op_mode, DEFAULT_COLOR)
        return f"op_mode_{op_mode}", color

    @system.tick(fps=20)
    def on_tick(self):
        current_time = monotonic()

        led_source, led_color = self.get_default_led_color()

        if led_source != self._previous_source:
            self._temporary_color = None

        if self._temporary_color is not None:
            led_color = self._temporary_color

        self._previous_source = led_source
        self._current_color = led_color

        # decide if LEDs should pulse
        if robot_state.is_thinking:
            if not self.is_pulsing:
                self.pulse_start_time = monotonic()
            self.is_pulsing = True
            self.stop_pulsing_requested = False
        else:
            self.stop_pulsing_requested = True

        # handle pulsing LEDs
        if self.is_pulsing:
            elapsed_time = (
                (current_time - self.pulse_start_time) * 2 * math.pi / PULSE_RATE
            )
            sine_value = math.cos(elapsed_time)
            intensity = (
                MIN_INTENSITY + (MAX_INTENSITY - MIN_INTENSITY) * (sine_value + 1) / 2
            )
            led_color = [intensity * x for x in self._current_color]

            if (
                elapsed_time >= 2 * math.pi
                and self.stop_pulsing_requested
                and abs(intensity - MAX_INTENSITY) < 0.05
            ):
                self.is_pulsing = False
                led_color = self._current_color

        self._set_lights(*led_color)
        probe("led_source", led_source)
        probe("led_color", led_color)
        probe("is_pulsing", self.is_pulsing)