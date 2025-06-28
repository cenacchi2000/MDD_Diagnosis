from time import time_ns as time_unix_ns
from collections import deque

custom_types = system.import_library("../lib/types.py")

stash = system.unstable.stash

perception_state = system.import_library("./perception_state.py").perception_state

world_face = system.import_library("./lib/world_face.py")
robot_state = system.import_library("../robot_state.py").state

ActiveSensor = system.import_library("../robot_state/ActiveSensor.py").ActiveSensor


class Activity:
    _vc_socket = None
    _sensors_view = None
    _chosen_sensor = None
    _video_capture_address = None

    async def on_start(self):

        self.frame_buffer_bytes = deque([None] * 3, 3)

        perception_state.last_image_bytes = None
        perception_state.last_good_image_bytes = None

        # Find active camera from mediapipe node
        self.mediapipe_checker = stash.subscribe(
            "/runtime/nodes/mediapipe/chosen_stream"
        )
        # Call update_mediapipe_sensor event when a change is detected
        self.mediapipe_checker.add_callback(self.on_update)

        self._sensors = stash.subscribe("/runtime/robot/sensors")
        self._sensors.add_callback(self.on_update)

    def on_update(self, data) -> None:
        if self.mediapipe_checker.data and self._sensors.data:
            self.mediapipe_sensor = self.mediapipe_checker.data["name"]
            self._on_video_sensors_updated(self._sensors.data)

    def _on_video_sensors_updated(self, data) -> None:
        if data is None:
            log.error("No sensor data found")
        else:
            # Set specified sensor to active sensor found in mediapipe
            specified_sensor = self.mediapipe_sensor
            robot_sensors = [item["name"] for item in data]
            if specified_sensor in robot_sensors:
                self._chosen_sensor = specified_sensor
            else:
                log.warning(
                    f"{specified_sensor} not found, defaulting to first video sensor found"
                )
                for sensor in data:
                    if sensor["type"] == "video":
                        self._chosen_sensor = sensor["name"]
                        break

            if self._chosen_sensor:
                log.info(f"{self._chosen_sensor} video sensor found")
                for sensor in data:
                    if sensor["name"] == self._chosen_sensor:
                        if mjpeg_stream := sensor["streams"]["mjpeg"]:
                            video_capture_address = mjpeg_stream["source"]["address"]
                            aspect_ratio = (
                                mjpeg_stream["properties"]["height"]
                                / mjpeg_stream["properties"]["width"]
                            )
                            world_face.WorldFace.aspect_ratio = aspect_ratio

                            if video_capture_address != self._video_capture_address:
                                self._video_capture_address = video_capture_address
                                self.reset_zmq_socket()

                                self._vc_socket = system.unstable.owner.subscribe_to(
                                    self._video_capture_address,
                                    self._on_video_capture_data,
                                    description="video frames",
                                    conflate=True,
                                )
                            ActiveSensor.set(
                                ActiveSensor(
                                    name=self._chosen_sensor,
                                    neutral=f"{self._chosen_sensor.split(' ', 1)[0]} Eye Neutral",
                                )
                            )
                            probe("Sensor Name", self._chosen_sensor)
                            probe("Video Capture Address", self._video_capture_address)
                            probe("Video Camera Aspect Ratio", aspect_ratio)

                            return
                        else:
                            probe("Video Capture Address", None)
                            log.warning(
                                f"Could not find a valid mjpeg encoded video stream for {sensor['name']}"
                            )
            else:
                log.error("No video sensor found")

    def _on_video_capture_data(self, data):
        time_ns = time_unix_ns()
        self.frame_buffer_bytes.appendleft((time_ns, data))
        perception_state.last_image_bytes = data

        if not robot_state.is_thinking and not robot_state.blinking:
            perception_state.last_good_image_bytes = data

    def reset_zmq_socket(self):
        try:
            import zmq
        except ImportError:
            pass
        else:
            if self._vc_socket:
                self._vc_socket.setsockopt(zmq.LINGER, 0)
        if hasattr(self, "_vc_socket"):
            try:
                system.unstable.owner._stop_listening_to(self._vc_socket)
            except Exception:
                pass
        self._vc_socket = None

    def on_stop(self):
        self.reset_zmq_socket()

        if self._sensors_view:
            self._sensors_view.close()