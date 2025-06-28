"""
=====================================================================================
Telepresence Face Mocap V1.0

Use instructions:
    1. Open telepresence UI page and select 'capture'. Connect through either methods available.
    2. Mouth will move best when telepresence audio output is enabled and flappy lipsync blends with mocap lip

=====================================================================================
"""

import sys
import math
import statistics
from time import monotonic as now
from socket import AF_INET, SHUT_RDWR, SOCK_DGRAM, socket
from threading import Event, Thread
from collections import namedtuple, defaultdict

from ea.util import yaml
from tritium.world.geom import Point3
from ea.animation.easing import outquart

KEEP_ALIVE_TIME = 2  # If 2 seconds no response from browser, reset face to neutral.
PING_INTERVAL = 0.5
CAPTURE_SILENCE_THRESHOLD = (
    0.25  # peak level < than this value will disable capture mouth
)
CAPTURE_JAW_SILENCE_THRESHOLD = (
    0.25  # (1-jaw open value) < this value will disable capture mouth
)
NEUTRAL_POSE = "AR_neutral"
Blendshape = namedtuple("Blendshape", "name,value")
WAIT_FOR_TELEPRESENCE_START = False
SELF_IDENTIFIER = "ADD_TELEPRESENCE_MOCAP"
MOUTH_OPEN_CONTROL = ("Mouth Open", "Mesmer Mouth 2")

# If we listen to audio_player we run the risk of suddenly opening the mouth when a
# sequence ends at the same time as an audio file it triggered.
AUDIO_SOURCES = ["telepresence"]
audio_levels = system.control("Audio Levels", None, acquire=AUDIO_SOURCES)


class Face_Mocap_Pose_Converter:
    def __init__(self, config, mirror=False):
        self.config = config

    def convert_blendshapes_to_mixed_controls(self, blendshapes):
        mixed_controls = self.config.convert(blendshapes)
        return mixed_controls

    def load_profile_config(self, config):
        self.config.load_profile_config(config)

    def load_base_config(self, config):
        """
        Config maps from AR kit to system poses
        """
        self.connections = {}
        self.conversion_dict = defaultdict(lambda: [])
        # Open the file and load the file
        try:
            data = yaml.safe_load(config)
            for d in data["connections"]:
                self.load_config_entry(**data["connections"][d])
            for d in data["post_process"]:
                self.load_post_process_entry(**data["post_process"][d])
        except Exception as e:
            print(
                "Unable to load FACELINK_CONFIG data", sys.exc_info()[0], "::", str(e)
            )


class Face_Mocap_Socket_Connection:
    """Connect to face link

    Opens UDP socket to IOS app : Facemotion3d
    Instructions: https://www.facemotion3d.info/instructions/

    """

    _ar_listen_thread = None
    _stop_ar_listen_thread_event = Event()
    _connected = False
    _started = False
    server = None

    def __init__(self, ip_address, dstPort, recvPort, on_ar_values_received):
        self.ip_address = ip_address
        self.dstPort = dstPort
        self.recvPort = recvPort
        self.on_ar_values_received = on_ar_values_received

    def reconnect(self):
        self.stop()
        dstAddr = (self.ip_address, self.dstPort)
        udpClntSock = socket(AF_INET, SOCK_DGRAM)
        data = "FACEMOTION3D_OtherStreaming"
        data = data.encode("utf-8")
        udpClntSock.sendto(data, dstAddr)
        self.server = socket(AF_INET, SOCK_DGRAM)
        self.server.bind(("", self.recvPort))  # Receving Port, Also shouldn't change
        self.server.settimeout(1 / 10)

    def is_same_address(self, ip_address, dstPort, recvPort):
        return (
            self.ip_address == self.ip_address
            and self.dstPort == dstPort
            and self.recvPort == recvPort
        )

    def parse_blendshapes(self, recv):
        blendshapes = []
        """First Parse the blendshapes, then according to connections config, do inversion etc."""
        recv = recv.split("|")
        for item in recv:
            if "&" in item:
                s_list = [item.split("&")]
            elif "#" in item:
                s_list = []
                vals = list(map(float, item[item.find("#") + 1 :].split(",")))
                for idx, name in enumerate(["Y", "X", "Z"]):
                    s_list.append(
                        [item.split("#")[0].replace("=", "") + name, vals[idx]]
                    )
            else:
                s_list = []
            blendshapes.append(blendshapes)
        return blendshapes

    def start_AR_Listen_Thread(self):
        self.reconnect()

        def ar_listen_loop():
            while not self._stop_ar_listen_thread_event.is_set():
                try:
                    messages, address = self.server.recvfrom(8192)
                    self.on_ar_values_received(self.parse_blendshapes(messages))
                    self._connected = True
                except OSError:
                    self._connected = False
                except TimeoutError:
                    self._connected = False
                    self.reconnect()
            self._stop_ar_listen_thread_event.clear()
            self._started = False

        if self._ar_listen_thread:
            self.stop_AR_Listen_Thread()

        self._ar_listen_thread = Thread(target=ar_listen_loop)
        self._ar_listen_thread.start()
        self._started = True

    def stop_AR_Listen_Thread(self):
        if self._ar_listen_thread:
            self._stop_ar_listen_thread_event.set()
            self._ar_listen_thread.join()
            self._ar_listen_thread = None

    def stop(self):
        """Called each time this control function object is deactivated"""
        self.stop_AR_Listen_Thread()
        if not self.server:
            return
        try:
            self.server.shutdown(SHUT_RDWR)
        except OSError:
            pass
        self.server.close()


class AR_Kit_Remote:
    def __init__(self, on_ar_values_received):
        self.socket_connection = None
        self.on_ar_values_recevied = on_ar_values_received

    def start(self, ip_address, dstPort=49983, recvPort=49983):
        if self.socket_connection is None:
            self.socket_connection = Face_Mocap_Socket_Connection(
                ip_address,
                dstPort,
                recvPort,
                on_ar_values_received=self.on_ar_values_received,
            )
        elif not self.socket_connection.is_same_address(ip_address, dstPort, recvPort):
            self.socket_connection.stop()
            self.socket_connection = Face_Mocap_Socket_Connection(
                ip_address,
                dstPort,
                recvPort,
                on_ar_values_received=self.on_ar_values_received,
            )
        self.socket_connection.start_AR_Listen_Thread()

    def stop(self):
        if self.socket_connection is not None:
            self.socket_connection.stop()

    @property
    def started(self):
        if self.socket_connection is not None:
            return self.socket_connection._started
        else:
            return False

    @property
    def connected(self):
        return self.socket_connection._connected


class MocapProfile:
    def __init__(
        self, sum_blendshapes, mix_blendshapes, post_process_values, neutral_pose
    ):
        self.sum_blendshapes = sum_blendshapes
        self.mix_blendshapes = mix_blendshapes

        self.profile_config = {}

        self.sum_converters = defaultdict(lambda: [])
        self.mix_converters = defaultdict(lambda: [])
        self.neutral_pose = system.poses.get(neutral_pose)

        for b in self.sum_blendshapes:
            b.set_neutral_pose(self.neutral_pose)
            self.sum_converters[b.blendshape_name].append(b)

        for b in self.mix_blendshapes:
            b.set_neutral_pose(self.neutral_pose)
            self.mix_converters[b.blendshape_name].append(b)

        self.post_process_values = post_process_values

    def load_profile_config(self, profile_config):
        self.profile_config = profile_config

    def convert(self, blendshapes):
        sum_converted = defaultdict(lambda: [])
        mix_converted = defaultdict(lambda: [])

        for blendshape in blendshapes:
            blendshape_name = blendshape.name
            blendshape_value = blendshape.value

            converters = self.sum_converters.get(blendshape_name, None)
            if converters is not None:
                for converter in converters:
                    converted_pose = converter.convert(Point3(blendshape_value))
                    for k, v in converted_pose.items():
                        sum_converted[k].append(v)

            converters = self.mix_converters.get(blendshape_name, None)
            if converters is not None:
                for converter in converters:
                    converted_pose = converter.convert(Point3(blendshape_value))
                    for k, v in converted_pose.items():
                        mix_converted[k].append(v)

        mixed = {}
        for k, values in sum_converted.items():
            gain, offset = self.profile_config.get(k, [1, 0])
            mixed[k] = offset + self.neutral_pose[k] + sum(values) * gain

        for k, values in mix_converted.items():
            gain, offset = self.profile_config.get(k, [1, 0])
            if mixed.get(k, None) is not None:
                mixed[k] = statistics.mean(
                    [
                        mixed[k],
                        self.neutral_pose[k] + statistics.mean(values) * gain * 0.5,
                    ]
                )
            else:
                mixed[k] = (
                    offset + self.neutral_pose[k] + statistics.mean(values) * gain * 0.5
                )

        for k in mixed:
            post_process = self.post_process_values.get(k, [])
            for process in post_process:
                mixed[k] = process(mixed[k])
        return mixed


class ProcessConfig:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, value):
        return value


class Offset(ProcessConfig):
    def __init__(self, offset: float = 0):
        self.offset = offset

    def __call__(self, value):
        return self.offset + value


class LinearGain(ProcessConfig):
    def __init__(self, gain: float = 1):
        self.gain = gain

    def __call__(self, value):
        return value * self.gain


class PlateauGain(ProcessConfig):
    def __init__(self, gain: float = 1):
        self.a = -max(0, min(50, gain))

    def __call__(self, value):
        return 1 - math.exp(self.a * value)


class Momentum(ProcessConfig):
    def __init__(self, B: float = 0.5, S: float = 0.3):
        self.B = B
        self.S = S
        self.prev_diff = 0
        self.prev_val = 0

    def __call__(self, value):
        diff = value - self.prev_val
        momentum_term = self.prev_diff * self.B + diff * (1 - self.B)
        value = momentum_term * self.S + value
        self.prev_diff = diff
        self.prev_val = value
        return value


class Decay(ProcessConfig):
    def __init__(self, D: float = 0.05, thresh: float = 0.5, max_decay: float = 1):
        self.decay = 0
        self.D = D
        self.thresh = thresh
        self.max_decay = max_decay

    def __call__(self, value):
        value -= self.decay
        if value > self.thresh:
            self.decay += self.D
        else:
            self.decay -= self.D

        self.decay = max(0, min(self.max_decay, self.decay))
        return value


class Smooth(ProcessConfig):
    def __init__(self, m: float = 0.5):
        self.m = m
        self.prev_val = 0

    def __call__(self, value):
        value = self.prev_val * self.m + value * (1 - self.m)
        self.prev_val = value
        return value


class Clip(ProcessConfig):
    def __init__(self, clip_lower: float = 0, clip_upper: float = 1):
        self.clip_lower = clip_lower
        self.clip_upper = clip_upper

    def __call__(self, value):
        return max(self.clip_lower, min(self.clip_upper, value))


class Ease(ProcessConfig):
    def __init__(self, easing_function):
        self.easing_function = easing_function

    def __call__(self, value):
        return self.easing_function(value)


class BlendshapeToPose:
    def __init__(
        self,
        blendshape_name: str,
        pose: str or dict,
        preprocess: [ProcessConfig] = [],
        postprocess: [ProcessConfig] = [],
    ):
        self.blendshape_name = blendshape_name
        if type(pose) is str:
            self.pose = system.poses.get(pose)
        else:
            self.pose = pose
        self.pose_offset_from_neutral = None
        self.preprocess = preprocess
        self.postprocess = postprocess

    def set_neutral_pose(self, neutral_pose):
        self.pose_offset_from_neutral = {}
        for k, v in neutral_pose.items():
            p_v = self.pose.get(k, None)
            if p_v is not None:
                self.pose_offset_from_neutral[k] = p_v - v

        # Extra assertion for cover
        for k, v in self.pose.items():
            assert neutral_pose.get(k, None) is not None

    def convert(self, value):
        for process in self.preprocess:
            value = process(value)

        converted = {}
        if self.pose_offset_from_neutral is None:
            pose_base = self.pose
        else:
            pose_base = self.pose_offset_from_neutral

        # Convert by scaling current pose
        for k, pose_v in pose_base.items():
            converted[k] = pose_v * value

        for process in self.postprocess:
            converted[k] = process(converted[k])

        return converted


class Activity:
    _last_pinged = now()
    ar_kit_plugin = None

    def on_start(self):
        self._prev_peak_level = 0
        self.telepresence_started = False
        self._prev_demands = {}
        self._last_blendshape_received = now()

        mocap_config = MocapProfile(
            sum_blendshapes=[
                BlendshapeToPose(
                    blendshape_name="jawOpen",
                    pose="AR_jawOpen",
                    preprocess=[LinearGain(0.5), PlateauGain(5), Clip(0, 0.7)],
                ),
                BlendshapeToPose(
                    blendshape_name="browInnerUp", pose="AR_browInnerUp", preprocess=[]
                ),
                BlendshapeToPose(
                    blendshape_name="browDownLeft",
                    pose="AR_browDownLeft",
                    preprocess=[],
                ),
                BlendshapeToPose(
                    blendshape_name="browDownRight",
                    pose="AR_browDownRight",
                    preprocess=[],
                ),
                BlendshapeToPose(
                    blendshape_name="browOuterUpLeft",
                    pose="AR_browOuterUpLeft",
                    preprocess=[],
                ),
                BlendshapeToPose(
                    blendshape_name="browOuterUpRight",
                    pose="AR_browOuterUpRight",
                    preprocess=[],
                ),
                BlendshapeToPose(
                    blendshape_name="browDownLeft", pose="AR_noseSneer", preprocess=[]
                ),
                BlendshapeToPose(
                    blendshape_name="browDownRight", pose="AR_noseSneer", preprocess=[]
                ),
                BlendshapeToPose(
                    blendshape_name="mouthFrownLeft",
                    pose="AR_mouthFrownLeft",
                ),
                BlendshapeToPose(
                    blendshape_name="mouthFrownRight",
                    pose="AR_mouthFrownRight",
                ),
                BlendshapeToPose(
                    blendshape_name="mouthRollUpper",
                    pose="AR_mouthRollUpper",
                    preprocess=[LinearGain(0.3), Clip(0, 1)],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthRollLower",
                    pose="AR_mouthRollLower",
                    preprocess=[LinearGain(0.3), Clip(0, 0.5)],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthShrugLower",
                    pose="AR_mouthShrugLower",
                    preprocess=[LinearGain(0.6), Clip(0, 0.5)],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthUpperUpLeft",
                    pose="AR_mouthUpperUpLeft",
                    preprocess=[
                        LinearGain(5),
                        PlateauGain(10),
                        Clip(0, 1),
                        Decay(0.15, 0.5),
                        Smooth(m=0.9),
                        Clip(0, 0.7),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthUpperUpRight",
                    pose="AR_mouthUpperUpRight",
                    preprocess=[
                        LinearGain(5),
                        PlateauGain(10),
                        Clip(0, 1),
                        Decay(0.15, 0.5),
                        Smooth(m=0.9),
                        Clip(0, 0.7),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthShrugUpper",
                    pose="AR_mouthShrugUpper",
                    preprocess=[
                        LinearGain(5),
                        PlateauGain(8),
                        Clip(0, 2),
                        Decay(0.15, 0.5),
                        Smooth(m=0.9),
                        Clip(0, 1),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthLowerDownLeft",
                    pose="AR_mouthLowerDownLeft",
                    preprocess=[
                        LinearGain(10),
                        PlateauGain(7),
                        Clip(0, 1),
                        Momentum(),
                        Decay(0.15, 0.5),
                        Smooth(m=0.5),
                        Clip(0, 1),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthLowerDownRight",
                    pose="AR_mouthLowerDownRight",
                    preprocess=[
                        LinearGain(10),
                        PlateauGain(7),
                        Clip(0, 1),
                        Momentum(),
                        Decay(0.15, 0.5),
                        Smooth(m=0.5),
                        Clip(0, 1),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthSmileLeft",
                    pose="AR_mouthSmileLeft",
                    preprocess=[
                        LinearGain(25),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthSmileRight",
                    pose="AR_mouthSmileRight",
                    preprocess=[
                        LinearGain(25),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthStretchLeft",
                    pose="AR_mouthStretchLeft",
                    preprocess=[
                        LinearGain(10),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthStretchRight",
                    pose="AR_mouthStretchRight",
                    preprocess=[
                        LinearGain(10),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="jawOpen",
                    pose={
                        ("Lip Corner Stretch Left", None): 1,
                        ("Lip Corner Stretch Right", None): 1,
                    },
                    preprocess=[LinearGain(2), Clip(0, 2)],
                ),
                BlendshapeToPose(
                    blendshape_name="eyeWideRight",
                    pose="AR_eyeWide",
                    preprocess=[LinearGain(30), Clip(0, 1)],
                ),
            ],
            mix_blendshapes=[
                BlendshapeToPose(
                    blendshape_name="mouthPucker",
                    pose="AR_mouthPucker",
                    preprocess=[
                        Offset(-0.87),
                        Ease(outquart),
                        LinearGain(100),
                        Clip(0, 2.2),
                        Decay(),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthStretchLeft",
                    pose="AR_mouthStretchLeft",
                    preprocess=[
                        LinearGain(10),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="mouthStretchRight",
                    pose="AR_mouthStretchRight",
                    preprocess=[
                        LinearGain(10),
                    ],
                ),
                BlendshapeToPose(
                    blendshape_name="eyeSquintLeft",
                    pose="AR_eyeSquint",
                    preprocess=[Offset(-0.3), LinearGain(10), Clip(0, 1)],
                ),
            ],
            post_process_values={
                ("Lip Top Raise Left", None): [Clip(0, 1)],
                ("Lip Top Raise Right", None): [Clip(0, 1)],
                ("Lip Top Raise Middle", None): [Clip(0, 1)],
                ("Nose", None): [Clip(0.5, 1)],
            },
            neutral_pose=NEUTRAL_POSE,
        )

        self.ar_kit_plugin = AR_Kit_Remote(self.on_blendshape_values_received)
        self.pose_converter = Face_Mocap_Pose_Converter(mocap_config)

    def on_stop(self):
        if self.ar_kit_plugin is not None:
            self.ar_kit_plugin.stop()
            system.messaging.post(
                "faceCapture",
                {
                    "type": "connection_status",
                    "data": {"Connected": False, "Status": "Not Connected"},
                },
            )
        self.try_clean_mix_pose()

    def on_message(self, channel, message):
        if channel == "telepresence":
            self.handle_telepresence(message)

    def convert_blendshape_format_from_browser_mediapipe_output(self, blendshapes):
        formatted_blendshapes = []
        for b in blendshapes:
            name = b["categoryName"]
            value = b["score"]
            formatted_blendshapes.append(Blendshape(name, value))
        return formatted_blendshapes

    def handle_telepresence(self, message):
        message_type = message.get("type", "")
        if message_type == "browser_blendshapes":
            blendshapes = (
                message.get("data", {}).get("blendshapes", {}).get("categories", {})
            )
            blendshapes = self.convert_blendshape_format_from_browser_mediapipe_output(
                blendshapes
            )
            self.on_blendshape_values_received(blendshapes)

        elif message_type == "session_active":
            message_value = message.get("value", False)
            self.telepresence_started = message_value
        elif message_type == "trigger_mocap":
            data = message.get("data", {})
            if data.get("connect", True):
                connection_ip = data.get("connection_ip", None)
                if connection_ip is not None:
                    self.ar_kit_plugin.start(connection_ip)
            else:
                self.ar_kit_plugin.stop()
        elif message_type == "load_profile":
            # Profile config values are between -1 and 1
            data = message.get("data", {})
            profile = data.get("profile", None)
            if profile is not None:
                brow_gain = profile.get("brow", 0)
                jaw_gain = profile.get("jaw", 0)
                smile_gain = profile.get("smile", 0)
                lip_gain = profile.get("lip", 0)
                nose_gain = profile.get("nose", 0)
                eyelid_gain = profile.get("eyelid", 0)

                brow_offset = profile.get("brow_offset", 0)
                jaw_offset = profile.get("jaw_offset", 0)
                smile_offset = profile.get("smile_offset", 0)
                lip_offset = profile.get("lip_offset", 0)
                nose_offset = profile.get("nose_offset", 0)
                eyelid_offset = profile.get("eyelid_offset", 0)

                smile_gain = 1 + smile_gain * 2
                jaw_gain = 1 + jaw_gain * 1.3
                brow_gain = 1 + brow_gain * 10
                lip_gain = 1 + lip_gain * 2
                nose_gain = 1 + nose_gain * 4
                eyelid_gain = 1 + eyelid_gain * 2

                eyelid_offset = eyelid_offset

                profile_config = {
                    ("Jaw Pitch", None): [jaw_gain, jaw_offset],
                    ("Lip Top Raise Middle", None): [lip_gain, lip_offset],
                    ("Lip Top Raise Left", None): [lip_gain, lip_offset],
                    ("Lip Top Raise Right", None): [lip_gain, lip_offset],
                    ("Lip Bottom Depress Middle", None): [lip_gain, lip_offset],
                    ("Lip Bottom Depress Left", None): [lip_gain, lip_offset],
                    ("Lip Bottom Depress Right", None): [lip_gain, lip_offset],
                    ("Lip Corner Raise Left", None): [smile_gain, smile_offset],
                    ("Lip Corner Raise Right", None): [smile_gain, smile_offset],
                    ("Brow Inner Left", "Mesmer Brows 1"): [brow_gain, brow_offset],
                    ("Brow Outer Left", "Mesmer Brows 1"): [brow_gain, brow_offset],
                    ("Brow Inner Right", "Mesmer Brows 1"): [brow_gain, brow_offset],
                    ("Brow Outer Right", "Mesmer Brows 1"): [brow_gain, brow_offset],
                    ("Nose Wrinkle", "Mesmer Nose 1"): [nose_gain, nose_offset],
                    ("Eyelid Lower Left", "Mesmer Eyelids 1"): [
                        eyelid_gain,
                        eyelid_offset,
                    ],
                    ("Eyelid Lower Right", "Mesmer Eyelids 1"): [
                        eyelid_gain,
                        eyelid_offset,
                    ],
                    ("Eyelid Upper Left", "Mesmer Eyelids 1"): [
                        eyelid_gain,
                        eyelid_offset,
                    ],
                    ("Eyelid Upper Right", "Mesmer Eyelids 1"): [
                        eyelid_gain,
                        eyelid_offset,
                    ],
                }
                self.pose_converter.load_profile_config(profile_config)

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

    def try_mix_pose_add_relative(self, k, v):
        if mix_pose := getattr(system.unstable.owner, "mix_pose", None):
            return mix_pose.add_relative(SELF_IDENTIFIER, k, v)
        else:
            return False

    def try_mix_pose_add_absolute(self, k, v):
        if mix_pose := getattr(system.unstable.owner, "mix_pose", None):
            return mix_pose.add_absolute(SELF_IDENTIFIER, k, v)
        else:
            return False

    def on_blendshape_values_received(self, values):
        self._last_blendshape_received = now()
        mixed_controls = self.pose_converter.convert_blendshapes_to_mixed_controls(
            values
        )
        self.control_pose(mixed_controls)

    def try_add_mouth_mix(self, ctrl, value):
        if mouth_driver := getattr(system.unstable.owner, "mouth_driver", None):
            mouth_driver.direct_control_add_mix(ctrl, value)

    def try_clean_mouth_mix(self):
        if mouth_driver := getattr(system.unstable.owner, "mouth_driver", None):
            mouth_driver.reset_direct_control_demands()

    def try_clean_mix_pose(self):
        if mix_pose := getattr(system.unstable.owner, "mix_pose", None):
            mix_pose.clean(SELF_IDENTIFIER)

    def reset_face(self):
        self.try_clean_mouth_mix()
        for item in self._prev_demands:
            k = item["key"]
            v = item["value"]
            k_lower = k[0].lower()
            if "head" in k_lower:
                continue
            elif "jaw" in k_lower:
                v = 1
            elif "brow" in k_lower:
                v = 0
            elif "eyelid" in k_lower:
                v = 1
            elif "nose" in k_lower:
                v = 0
            self.try_mix_pose_add_relative(k, v)
        self.try_clean_mix_pose()

    def control_pose(self, mixed_controls):
        """Do the demanding"""
        peak_level = audio_levels.telepresence if audio_levels.telepresence else 0
        smoothed_peak_level = peak_level * 0.5 + self._prev_peak_level * 0.5
        self._prev_peak_level = peak_level

        jaw_open_demand = mixed_controls.get(("Jaw Pitch", None))
        if jaw_open_demand is None or (
            smoothed_peak_level < CAPTURE_SILENCE_THRESHOLD
            and (1 - jaw_open_demand) < CAPTURE_JAW_SILENCE_THRESHOLD
        ):
            silence = True
        else:
            silence = False
        probe("peak_level", smoothed_peak_level)
        probe("jaw_open", (1 - jaw_open_demand))
        probe("silence", silence)

        neutral = system.poses.get(NEUTRAL_POSE)
        demanded_values = []
        for k, v in mixed_controls.items():
            n = neutral.get(k, None)
            k_lower = k[0].lower()
            if "lip" in k_lower:
                if silence and "corner" not in k_lower:
                    v = neutral.get(k)
                self.try_add_mouth_mix(k[0], v)
            else:
                if "head" in k_lower:
                    continue
                elif "jaw" in k_lower:
                    k = MOUTH_OPEN_CONTROL
                    v = 2 - v * 2
                elif "brow" in k_lower:
                    v = v - n

                try:
                    self.try_mix_pose_add_relative(k, v)
                    demanded_values.append({"key": k, "value": v})
                except KeyError:
                    pass
        system.messaging.post("mocap_demands", {"demandedValues": demanded_values})
        self._prev_demands = demanded_values

    @system.tick(fps=1 / PING_INTERVAL)
    def on_tick(self):
        probe("started", self.ar_kit_plugin.started)
        if now() - self._last_blendshape_received > KEEP_ALIVE_TIME:
            self.reset_face()
            system.messaging.post(
                "mocap_connection_status",
                {"connected": False, "status": "Not Connected"},
            )
        elif now() - self._last_pinged > PING_INTERVAL:
            self._last_pinged = now()
            if self.ar_kit_plugin.started and self.ar_kit_plugin.connected:
                system.messaging.post(
                    "mocap_connection_status",
                    {"connected": True, "status": "Connected"},
                )
            elif self.ar_kit_plugin.started:
                system.messaging.post(
                    "mocap_connection_status",
                    {"connected": False, "status": "Connecting..."},
                )
            else:
                system.messaging.post(
                    "mocap_connection_status",
                    {"connected": False, "status": "Not Connected"},
                )