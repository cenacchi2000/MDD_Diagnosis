import random
from time import monotonic

CONFIG = system.import_library("../../Config/HB3.py").CONFIG

FLAPPY_GAIN = CONFIG["FLAPPY_GAIN"]
FLAPPY_SILENCE_THRESHOLD = CONFIG["FLAPPY_SILENCE_THRESHOLD"]

SELF_IDENTIFIER = "ADD_LIPSYNC"

CONTROL_NAMESPACE = "Mesmer Mouth 2"

CONTROL_NAMES = system.import_library("../Actuation/lib/visemes.py").CONTROL_NAMES
TextToSpeechNodeClient = system.import_library(
    "../Actuation/lib/tts_client.py"
).TextToSpeechNodeClient

FLAPPY_OPEN_CONTROL = (
    ["Viseme U"] * 2
    + ["Viseme I"] * 5
    + ["Viseme A"] * 5
    + ["Viseme E"] * 2
    + ["Viseme KK"] * 5
    + ["Viseme O"] * 3
    + ["Viseme SS"] * 3
)


AUDIO_SOURCES = ["polly", "telepresence", "espeak", "audio_player", "service_proxy"]
# If we listen to audio_player we run the risk of suddenly opening the mouth when a
# sequence ends at the same time as an audio file it triggered.
FLAPPY_SOURCES = ["telepresence", "espeak"]
audio_levels = system.control("Audio Levels", None, acquire=AUDIO_SOURCES)


class FlappyMouth:
    def __init__(
        self,
        peak_velocity: float = 0,
        peak_drop_rate: float = 1.2 * 60,
        peak_rise_rate: float = 1.1 * 60,
        flappy_change_chance: float = 15,  # number of times a second to change on average
        flappy_change_fade_out_rate: float = 18,
        peak_smoothing: float = 0.05,
        flappy_up_max_duration: float = 0.05,
        flappy_up_drop_duration: float = 0.05,
        flappy_up_threshold: float = 0.3,
        flappy_gain: float = 2.5,  # OVERWRITTEN BY CONFIG
    ):
        self.peak_velocity = peak_velocity
        self.peak_drop_rate = peak_drop_rate
        self.peak_rise_rate = peak_rise_rate
        self.flappy_change_chance = flappy_change_chance
        self.flappy_change_fade_out_rate = flappy_change_fade_out_rate
        self.peak_smoothing = peak_smoothing

        self.flappy_up_max_duration = flappy_up_max_duration
        self.flappy_up_drop_duration = flappy_up_drop_duration
        self.flappy_up_threshold = flappy_up_threshold

        self.flappy_up_started = False
        self.flappy_up_started_time = 0
        self.flappy_dropping_started_time = 0
        self.peak_level_gain = flappy_gain

        self.current_flappy_control = None
        self.get_next_flappy_control()
        self.prev_peak_level = 0
        self.current_demands = {}
        self._last_flappy = monotonic()

    def get_next_flappy_control(self):
        pending_next_control = self.current_flappy_control
        while pending_next_control == self.current_flappy_control:
            pending_next_control = random.choice(FLAPPY_OPEN_CONTROL)
        self.current_flappy_control = pending_next_control

    def fade_out_viseme_demands(self, gain):
        for ctrl in FLAPPY_OPEN_CONTROL:
            demand = self.current_demands.get(ctrl, 0)
            if demand:
                demand = max(0, demand - gain)
                self.current_demands[ctrl] = demand

    def do_flappy(self, peak_level):
        now = monotonic()
        delta_time = now - self._last_flappy
        self._last_flappy = now

        # Smooth the peak level we recieve slightly
        peak_level = (
            peak_level * (1 - self.peak_smoothing)
            + self.prev_peak_level * self.peak_smoothing
        )
        if peak_level < FLAPPY_SILENCE_THRESHOLD:
            peak_level = 0
        # Adjust this current velocity of mouth movement
        # Based on the change in peak level this frame
        self.peak_velocity = peak_level - self.prev_peak_level
        if self.peak_velocity < 0:
            modifier = self.peak_drop_rate * delta_time
        else:
            modifier = self.peak_rise_rate * delta_time
        # Apply the calculated velocity for this frame. With an adjustment based on the direction
        peak_level = self.prev_peak_level + self.peak_velocity * modifier
        self.prev_peak_level = peak_level
        # If flappy up for too long, drop down.

        if peak_level > self.flappy_up_threshold:
            self.flappy_up_started_time = now
            if random.random() < self.flappy_change_chance * delta_time:
                self.get_next_flappy_control()

        if self.flappy_up_started_time:
            if now - self.flappy_up_started_time > self.flappy_up_max_duration:
                self.flappy_up_started_time = 0
                self.flappy_dropping_started_time = now
                self.get_next_flappy_control()

        if self.flappy_dropping_started_time:
            if now - self.flappy_dropping_started_time > self.flappy_up_drop_duration:
                self.flappy_dropping_started_time = 0
                self.get_next_flappy_control()
                # self.fade_out_viseme_demands(1)
            else:
                peak_level = min(0, peak_level)

        self.fade_out_viseme_demands(self.flappy_change_fade_out_rate * delta_time)

        for k, v in self.current_demands.items():
            probe(k, v)

        peak_level *= self.peak_level_gain
        self.current_demands[self.current_flappy_control] = peak_level
        return self.current_demands


class Activity:
    def on_start(self):
        self.flappy_mouth = FlappyMouth(flappy_gain=FLAPPY_GAIN)

    def mix_pose_add_relative(self, ctrl, val):
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        if mix_pose is not None:
            mix_pose.add_relative(SELF_IDENTIFIER, ctrl, val)

    def mix_pose_clean_self(self):
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        if mix_pose is not None:
            mix_pose.clean(SELF_IDENTIFIER)

    def decorate_viseme_control_path(self, viseme):
        return (viseme, CONTROL_NAMESPACE)

    def on_stop(self):
        self.mix_pose_clean_self()

    def reset_visemes(self):
        for ctrl in CONTROL_NAMES:
            self.mix_pose_add_relative(self.decorate_viseme_control_path(ctrl), 0)
        self._current_demands = {}

    def get_max_audio_source(self):
        max_val = 0
        max_val_source = None
        for audio_source in AUDIO_SOURCES:
            val = getattr(audio_levels, audio_source)
            probe(audio_source, val)
            if val is not None and val > max_val:
                max_val = val
                max_val_source = audio_source
        return max_val, max_val_source

    @system.tick(fps=60)
    def on_tick(self):
        peak_level, peak_level_source = self.get_max_audio_source()
        probe("peak", peak_level)

        if peak_level_source not in FLAPPY_SOURCES:
            queue = TextToSpeechNodeClient.get_current_viseme_queue()

            if queue is None or not queue.is_playable():
                self.reset_visemes()
            else:
                samples = queue.sample()

                for ctrl, val in samples.items():
                    if val is not None:
                        self.mix_pose_add_relative(
                            self.decorate_viseme_control_path(ctrl), val
                        )
        else:
            flappy_demands = self.flappy_mouth.do_flappy(peak_level)
            for k, v in flappy_demands.items():
                self.mix_pose_add_relative(self.decorate_viseme_control_path(k), v)