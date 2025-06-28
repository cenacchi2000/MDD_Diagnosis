"""
    This feature implementation is meant combat interaction degredation over long periods of operation time.
    It does this by resetting the robot state interaction history if there is a timeframe of inactivity.
    To edit the inactivity duration necessary for interaction reset, please edit INACTIVITY_TIME_THRESHOLD.
"""

import time

ROBOT_STATE = system.import_library("../robot_state.py")
CONFIG = system.import_library("../../Config/Chat.py").CONFIG
INACTIVITY_TIME_THRESHOLD = CONFIG["INTERACTION_REFRESH_INACTIVITY_THRESHOLD"]

default_voice_reset_evt = system.event("default_voice_reset")


class Activity:
    def __init__(self):
        self.inactivity_start = time.monotonic()
        self.activity_refresh = False
        self.is_clean_history = True

    @system.tick(fps=10)
    def on_tick(self):
        self.probe_states()
        self.reset_inactivity_timer()
        if self.get_inactivity_time() >= self.min_to_seconds(INACTIVITY_TIME_THRESHOLD):
            ROBOT_STATE.interaction_history.reset()
            self.reset_states()
            print("Resetting Interaction History")

    @system.on_event("tts_idle")
    def on_tts_finished(self, _) -> None:
        self.activity_refresh = True
        self.is_clean_history = False

    @system.on_event("speech_recognized")
    def on_speech_rec(self, _) -> None:
        self.activity_refresh = True
        self.is_clean_history = False

    def reset_inactivity_timer(self) -> None:
        """
        Resets the inactivity timer if:
            - There is a new interaction.
            - The interaction history is clear.
        """
        if self.activity_refresh or self.is_clean_history:
            self.inactivity_start = time.monotonic()
            self.activity_refresh = False

    def get_inactivity_time(self) -> float:
        """
        Returns the time since the last interaction.
        """
        return time.monotonic() - self.inactivity_start

    def reset_states(self) -> None:
        """
        Resets the script to default state.
        """
        self.activity_refresh = False
        self.is_clean_history = True
        default_voice_reset_evt.emit(__file__)

    def probe_states(self) -> None:
        """
        Displays telemetry in the debug data tab.
        """
        probe("Inactivity time (seconds):", self.get_inactivity_time())
        probe(
            "Inactivity Time Threshold (seconds):",
            self.min_to_seconds(INACTIVITY_TIME_THRESHOLD),
        )
        probe("Inactivity start time:", self.inactivity_start)
        probe("Has Been Refreshed:", self.activity_refresh)
        probe("Is a Clean History:", self.is_clean_history)

    def min_to_seconds(self, minutes: float) -> float:
        """
        Helper function to convert minutes to seconds.
        """
        return minutes * 60