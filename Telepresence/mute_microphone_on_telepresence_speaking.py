"""
QDH mute microphone on telepresence speaker output
"""

from time import monotonic as now

audio_levels = system.control("Audio Levels", None, acquire=["telepresence"])
robot_mic_mute = system.control("Microphone Mute", None)

MUTE_THRESH = 0.2
MUTE_LINGER = 0.35


class Activity:
    def on_start(self):
        self._last_muted_t = 0

    def on_stop(self):
        robot_mic_mute.demand = False

    @system.tick(fps=50)
    def on_tick(self):
        peak_level = audio_levels.telepresence
        probe("peak_level", peak_level)
        if peak_level is None:
            robot_mic_mute.demand = False
            probe("mic_muted", False)
            return

        mute_lingering = (now() - self._last_muted_t) < MUTE_LINGER
        if peak_level > MUTE_THRESH:
            self._last_muted_t = now()
            robot_mic_mute.demand = True
            probe("mic_muted", True)
        elif mute_lingering:
            robot_mic_mute.demand = True
            probe("mic_muted", True)
        else:
            robot_mic_mute.demand = False
            probe("mic_muted", False)