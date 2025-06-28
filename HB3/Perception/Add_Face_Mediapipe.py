from tritium.world.geom import Rect, Vector2

custom_types = system.import_library("../lib/types.py")

ActiveSensor = system.import_library("../robot_state/ActiveSensor.py").ActiveSensor

FaceDetection = custom_types.FaceDetection
DetectedFace = custom_types.DetectedFace


class Activity:
    _publisher = None

    def on_start(self):
        self._mp_socket = system.unstable.owner.subscribe_to(
            "ipc:///run/tritium/sockets/mediapipe_data",
            self._on_mediapipe_data,
            expect_json=True,
            description="mediapipe events",
            conflate=True,
        )

        if ActiveSensor.get().name:
            self._publisher = system.world.publish(
                "face_detections", FaceDetection, ActiveSensor.get().name
            )

    @ActiveSensor.subscribe()
    def on_sensor_updated(self, sensor) -> None:
        self._publisher = system.world.publish(
            "face_detections", FaceDetection, sensor.name
        )

    def _on_mediapipe_data(self, data):
        fds = data.get("face_detections", [])
        faces = []
        if fds and isinstance(fds[0], list):
            # This is for backwards compatibility of the mediapipe node.
            # It no longer has this nested list.
            fds = fds[0]
        for i, fd in enumerate(fds):
            rbbox = fd["locationData"]["relativeBoundingBox"]
            faces.append(
                DetectedFace(
                    i,
                    Rect(
                        [rbbox["xmin"], rbbox["ymin"], rbbox["width"], rbbox["height"]]
                    ),
                    fd["score"][0],
                    [
                        Vector2([kp["x"], kp["y"]])
                        for kp in fd["locationData"]["relativeKeypoints"]
                    ],
                )
            )
        if self._publisher:
            self._publisher.write(
                FaceDetection(faces, ActiveSensor.get().name, data["time_ns"])
            )

    def on_stop(self):
        try:
            import zmq
        except ImportError:
            pass
        else:
            self._mp_socket.setsockopt(zmq.LINGER, 0)
        system.unstable.owner._stop_listening_to(self._mp_socket)
        self._mp_socket = None