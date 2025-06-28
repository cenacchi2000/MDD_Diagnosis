import zmq

"""
Set poses remotely via keyboard presses to compare robots
"""
# Run this on your machine to control the robot via zmq
"""
import zmq
import time
import readkeys

KEYMAP = {
    'a': "Viseme A",
    's': "Viseme CH",
    'd': "Viseme Closed",
    'f': "Viseme E",
    'g': "Viseme F",
    'h': "Viseme I",
    'j': "Viseme ING",
    'z': "Viseme KK",
    'x': "Viseme M",
    'c': "Viseme NN",
    'v': "Viseme O",
    'b': "Viseme RR",
    'n': "Viseme SS",
    'm': "Viseme U",
    '1': "HB3_Body_Neutral",
    '2': "HB3_Basic_Shrug",
    '3': "HB3_Hand_Clench",
    '4': "HB3_Left_Point_A",
    '5': "HB3_Left_Point_A2",
    '6': "HB3_Left_Point_B",
    '7': "HB3_Left_Point_B1",
    'w': "HB3_Left_Raise",
    'e': "HB3_Left_Raise_B",
    'r': "HB3_Low_Arms",
    't': "HB3_Palm_Base",
    'y': "HB3_Palm_Peak",
    'u': "HB3_Wide_Base",
    'i': "HB3_Wide_Peak",
}


class ZMQServer:
    def __init__(self, port=5555):
        self.context = zmq.Context()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://*:%s" % port)
    def send_value(self, topic, data):
        self.socket.send_string("{} {}".format(topic, data))

p = ZMQServer()

while True:
    key = readkeys.getch()
    if key == "q":
        p.send_value("stop", 1)
        exit(0)
    else:
        if key in KEYMAP:
            pose_name = KEYMAP[key]
            print(pose_name)
            p.send_value("pose", pose_name)
        else:
            print("No pose:", key)

"""


class Activity:
    scripts_to_stop = ["HB3/HB3_Controller.py", "Tests/Auto Playlist.py"]

    known_controls = [
        ("Lip Corner Raise Left", None),
        ("Lip Corner Raise Right", None),
        ("Jaw Pitch", None),
        ("Jaw Yaw", "Mesmer Mouth 2"),
        ("Lip Corner Stretch Left", None),
        ("Lip Corner Stretch Right", None),
        ("Lip Bottom Depress Left", None),
        ("Lip Bottom Depress Right", None),
        ("Lip Bottom Depress Middle", None),
        ("Lip Top Raise Left", None),
        ("Lip Top Raise Middle", None),
        ("Lip Top Raise Right", None),
        ("Lip Top Curl", None),
        ("Lip Bottom Curl", None),
        ("Elbow Pitch Left", "Mesmer Arms 1"),
        ("Wrist Pitch Left", "Mesmer Arms 1"),
        ("Wrist Roll Left", "Mesmer Arms 1"),
        ("Wrist Yaw Left", "Mesmer Arms 1"),
        ("Elbow Pitch Right", "Mesmer Arms 1"),
        ("Wrist Pitch Right", "Mesmer Arms 1"),
        ("Wrist Roll Right", "Mesmer Arms 1"),
        ("Wrist Yaw Right", "Mesmer Arms 1"),
        ("Clavicle Roll Left", "Mesmer Arms 1"),
        ("Clavicle Yaw Left", "Mesmer Arms 1"),
        ("Shoulder Pitch Left", "Mesmer Arms 1"),
        ("Shoulder Roll Left", "Mesmer Arms 1"),
        ("Shoulder Yaw Left", "Mesmer Arms 1"),
        ("Clavicle Roll Right", "Mesmer Arms 1"),
        ("Clavicle Yaw Right", "Mesmer Arms 1"),
        ("Shoulder Pitch Right", "Mesmer Arms 1"),
        ("Shoulder Roll Right", "Mesmer Arms 1"),
        ("Shoulder Yaw Right", "Mesmer Arms 1"),
        ("Brow Inner Left", "Mesmer Brows 1"),
        ("Brow Inner Right", "Mesmer Brows 1"),
        ("Brow Outer Left", "Mesmer Brows 1"),
        ("Brow Outer Right", "Mesmer Brows 1"),
        ("Index Finger Left", "Mesmer Fingers 1"),
        ("Index Finger Right", "Mesmer Fingers 1"),
        ("Little Finger Left", "Mesmer Fingers 1"),
        ("Little Finger Right", "Mesmer Fingers 1"),
        ("Middle Finger Left", "Mesmer Fingers 1"),
        ("Middle Finger Right", "Mesmer Fingers 1"),
        ("Ring Finger Left", "Mesmer Fingers 1"),
        ("Ring Finger Right", "Mesmer Fingers 1"),
        ("Head Yaw", "Mesmer Neck 1"),
        ("Neck Pitch", "Mesmer Neck 1"),
        ("Torso Pitch", "Mesmer Torso 1"),
        ("Torso Roll", "Mesmer Torso 1"),
        ("Torso Yaw", "Mesmer Torso 1"),
    ]
    controls = {
        (c, n): system.control(c, n, required=False) for (c, n) in known_controls
    }

    def on_start(self):
        for s in self.scripts_to_stop:
            self.stop_script(s)

        host = "tcp://mypc"
        port = 5555
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("{}:{}".format(host, port))
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

    def on_stop(self):
        for s in self.scripts_to_stop:
            self.start_script(s)

        try:
            if self.socket:
                self.socket.close()
        except Exception:
            self.socket = None
        pass

    def check_new_message(self):
        try:
            message = self.socket.recv(flags=zmq.NOBLOCK)
            data = message.decode().split(" ", 1)
            topic = data[0]
            value = data[1]
            return (topic, value)
        except zmq.Again:
            return None
            pass

    def start_script(self, script_path):
        return system.unstable.state_engine.start_activity(
            cause=f"started by script: {system._path!r}",
            activity_class="script",
            properties={
                "script": script_path
                # TODO: Don't hardcode this!
                # "script_file_path": f"/var/opt/tritium/scripts/{script_path}",
            },
        )

    def stop_script(self, script_path):
        for activity in system.unstable.state_engine._state.activities:
            if activity.get_property("script") == script_path:
                # TODO: don't rely on this private attribute
                system.unstable.state_engine.stop_activity(
                    f"stopped by script: {system._path!r}", activity
                )

    def apply_pose(self, pose):
        for ctrl, val in pose.items():
            if ctrl in self.controls:
                self.controls[ctrl].demand = val
            else:
                print("Control not found: ", ctrl)

    @system.tick(fps=100)
    def on_tick(self):
        msg = self.check_new_message()
        if msg:
            (topic, value) = msg
            if topic == "stop":
                self.stop()
            if topic == "pose":
                try:
                    pose = system.poses.get(value)
                    if pose:
                        self.apply_pose(pose)
                except Exception:
                    print(f"Pose not found: {value}")

        pass