match_detections = system.import_library("./lib/match_detections.py")

custom_types = system.import_library("../lib/types.py")

FaceDetection = custom_types.FaceDetection
DetectedFace = custom_types.DetectedFace

perception_state = system.import_library("./perception_state.py").perception_state

world_object = system.import_library("./lib/world_object.py")
WorldObject = world_object.WorldObject

# CONSTANTS
MIN_FACE_DETECTION_CONFIDENCE = 0.7

ActiveSensor = system.import_library("../robot_state/ActiveSensor.py").ActiveSensor

world_face = system.import_library("./lib/world_face.py")
WorldFaceObservation = world_face.WorldFaceObservation
WorldFace = world_face.WorldFace
robot_state = system.import_library("../robot_state.py").state

SUB_NAME = "face_detections"
PUB_NAME_2D = "face_detections_filtered"
PUB_NAME_3D = "faces"


class Activity:
    world_faces = set()
    detection_coroutines = {}
    sub = None
    object_counter = 0
    processing_coroutine = None
    MIN_FACE_CONFIDENCE = 0.1

    async def on_start(self):

        # Spin up coroutines to
        self.pubs_2d = {}
        self.pubs_3d = {}

        self.pub_2d = system.world.publish(
            PUB_NAME_2D, FaceDetection, ActiveSensor.get().name
        )

        self.pub_3d = system.world.publish(
            PUB_NAME_3D,
            custom_types.DetectedFace3D,
            system.world.ROBOT_SPACE,
            display=[
                {"with": "/position", "shape": "sphere", "color": "red", "size": 0.03},
                {"tether": {"color": "skyblue", "linewidth": 6}},
                {"shape": "axes", "size": 0.2},
                {"with": "/saccades", "size": 0.02, "color": "green"},
                "speak",
                {"label": "name"},
            ],
        )

        async with system.world.query_features(name=SUB_NAME) as sub:
            async for s in sub.async_iter():
                if s is not None:
                    self.process_camera_observations(s)

    @ActiveSensor.subscribe()
    def on_sensor_updated(self, sensor) -> None:
        self.pub_2d = system.world.publish(PUB_NAME_2D, FaceDetection, sensor.name)

    def on_stop(self):
        # Make sure all the update tasks are cancelled
        if self.processing_coroutine:
            self.processing_coroutine.cancel()

    def _get_filtered_observations(self, camera_observation):
        sample_time_ns = camera_observation.time_ns

        converter = system.world.converter(
            camera_observation.frame, system.world.ROBOT_SPACE
        )
        world_object_observations = []
        for detection in camera_observation.detections:
            if detection.confidence > MIN_FACE_DETECTION_CONFIDENCE:
                if (
                    (
                        world_object_observation := WorldFaceObservation.from_camera_observation(
                            detection, converter, sample_time_ns
                        )
                    )
                ) is None:
                    return None
                world_object_observations.append(world_object_observation)

        return world_object_observations

    def _update_faces_from_observations(
        self,
        world_object_observations: list[WorldFaceObservation],
        sample_time_s: float,
        arrangement: list[WorldFace, int],
        out_of_frame_faces: set[WorldFace],
    ):
        observation_indexes = set(range(len(world_object_observations)))
        observations_filtered = []
        for face, observation_index in arrangement:
            if observation_index is not None:
                world_object_observation = world_object_observations[observation_index]
                detection = world_object_observation.detection
                # A face has been detected. Update it
                observation_indexes.remove(observation_index)
                face.update(world_object_observation, sample_time_s)

                observations_filtered.append(
                    DetectedFace(
                        face.id,
                        detection.rect,
                        detection.confidence,
                        detection.keypoints,
                        (
                            face.info.get("name", None)
                            if face.info is not None
                            else "Unknown"
                        ),
                        detection.face_pose,
                    )
                )
            else:
                # A face has not been detected
                # Reduce the probability of the face if we expect to have seen it
                face.update_no_detection()

        # New faces
        for observation_index in observation_indexes:
            detection = world_object_observations[observation_index].detection
            face = WorldFace.from_observation(
                world_object_observations[observation_index],
                sample_time_s,
                id_=self.object_counter,
            )
            perception_state.world_faces.add(face)

            observations_filtered.append(
                DetectedFace(
                    face.id,
                    detection.rect,
                    detection.confidence,
                    detection.keypoints,
                    face.info.get("name", None) if face.info is not None else "Unknown",
                    detection.face_pose,
                )
            )
            self.object_counter += 1

        for face in out_of_frame_faces:
            face.update_out_of_frame()

        return observations_filtered

    def _update_faces_after_observations(self, sample_time_s: float):
        faces_by_id = {}
        faces_with_no_id = set()

        for face in perception_state.world_faces:
            # Drop faces which are too low probability or timed out
            if face.confidence < self.MIN_FACE_CONFIDENCE or (
                sample_time_s - face.last_update_time > face.TIMEOUT_S
            ):
                continue
            if face.profile_id is None:
                faces_with_no_id.add(face)
                continue
            # Merge faces which have been recognised as having the same ID
            elif face.profile_id in faces_by_id:
                if face.confidence < faces_by_id[face.profile_id].confidence:
                    continue
            faces_by_id[face.profile_id] = face

        new_world_faces = faces_with_no_id.union(set([v for v in faces_by_id.values()]))

        for dropped_face in perception_state.world_faces - new_world_faces:
            perception_state.drop_face(dropped_face)
        perception_state.world_faces = new_world_faces

    def process_camera_observations(self, camera_observation):
        sample_time_ns = camera_observation.time_ns
        sample_time_s = sample_time_ns / 1e9

        # This function will save the image frame to robot state

        # Drop low confidence detections
        world_object_observations = self._get_filtered_observations(camera_observation)

        if world_object_observations is None:
            return None

        # Update the face location predictions based on the time step
        [face.predict(sample_time_s) for face in perception_state.world_faces]

        # Match the detections to the faces
        arrangement, out_of_frame_faces = match_detections.match_observations_to_faces(
            sample_time_ns,
            system.world.converter(system.world.ROBOT_SPACE, camera_observation.frame),
            world_object_observations,
        )

        observations_filtered = self._update_faces_from_observations(
            world_object_observations, sample_time_s, arrangement, out_of_frame_faces
        )

        self._update_faces_after_observations(sample_time_s)

        if self.pub_2d:
            self.pub_2d.write(
                FaceDetection(
                    observations_filtered, camera_observation.frame, sample_time_ns
                )
            )
        self.pub_3d.write(
            [
                face.to_viz_data(sample_time_ns)
                for face in perception_state.world_faces
                if face.observations_to_mature == 0
            ]
        )

    def on_message(self, channel, message):
        if channel == "remember_name":
            print(f"REMEMBER NAME of {message}")
            self.remember_name(message)

    def remember_name(self, name):
        try:
            unknown_people = [
                obj for obj in perception_state.world_faces["faces"] if obj.name is None
            ]
        except TypeError:
            return
        if len(unknown_people) != 1:
            print(
                f"Cannot work out who to name: there are {len(unknown_people)} unknown people in front of me."
            )
        else:
            unknown_people[0].remember_name(name)