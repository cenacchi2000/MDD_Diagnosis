import time
import asyncio
from math import pi, exp, pow, sin, acos, sqrt, atan2
from typing import List, Optional
from collections import deque

from PIL.Image import Image
from tritium.world.geom import Ray3, Point2, Point3, Matrix3, Matrix4, Vector2
from tritium.world.frames import FrameConverter

PROFILES = system.import_library("../../chat/knowledge/profiles.py")
INTERACTION_HISTORY = system.import_library(
    "../../chat/knowledge/interaction_history.py"
)
ROBOT_STATE = system.import_library("../../robot_state.py")
world_object = system.import_library("./world_object.py")

WorldObject = world_object.WorldObject

types = system.import_library("../../lib/types.py")
DetectedFace = types.DetectedFace
DetectedFace3D = types.DetectedFace3D

kalman_filter = system.import_library("./kalman_filter.py")
KalmanFilter3D = kalman_filter.KalmanFilter3D

perception_state = system.import_library("../perception_state.py").perception_state

face_embedding_client_module = system.import_library("./face_embedding_client.py")
profiles_client_module = system.import_library("./profiles_client.py")

face_embedding_client = face_embedding_client_module.FaceEmbeddingClient()
profiles_client = profiles_client_module.ProfilesClient()

# Human standard measurements from:
# https://en.wikipedia.org/wiki/Human_head#:~:text=Average%20head%20sizes,-Some%20values%20in&text=In%20particular%2C%20a%20random%20biocular,average%20value%20for%20biocular%20breadth.
DISTANCE_EYE_TO_EYE = 0.025
DISTANCE_NOSE_JUT = 0.015
DISTANCE_NOSE_HEAD_BACK = 0.085
DISTANCE_EYES_NOSE_VERTICAL = 0.028
DISTANCE_EYES_MOUTH_VERTICAL = 0.065
DISTANCE_EAR_TO_EAR = 0.0585

PI_TIMES_2_CUBED = pow(pi * 2, 3)


class WorldFaceObservation:
    def __init__(
        self,
        detection: DetectedFace,
        estimated_distance: float,
        saccade_rays: list[Ray3],
        left_right: bool,
        eye_distance_norm: float,
        center_ray: Ray3,
        events: Optional[List[str]] = None,
        speaking: Optional[float] = None,
    ):
        self.identifier = detection.identifier
        self.estimated_distance = estimated_distance
        self.saccade_rays = saccade_rays
        self.left_right = left_right
        self.eye_distance_norm = eye_distance_norm
        self.center_ray = center_ray
        self.events = events
        self.speaking = speaking
        self.confidence = detection.confidence
        self.detection = detection

    @classmethod
    def from_camera_observation(
        cls,
        camera_observation: DetectedFace,
        converter: FrameConverter,
        sample_time_ns: int,
    ):
        rays = [
            converter.convert(Point2(kp), sample_time_ns)
            for kp in camera_observation.keypoints
        ]
        if any([r is None for r in rays]):
            log.warning(
                "Unable to convert camera observation to rays because of missing reference frame information"
            )
            return None
        eye_right_ray, eye_left_ray, nose_ray, mouth_ray, _, _ = rays
        center_ray = nose_ray

        # Assume that face is level.
        # Also assume that mouth and eyes are all vertically in line
        eye_center_mouth_vec = (
            eye_right_ray.direction + eye_left_ray.direction
        ) / 2 - mouth_ray.direction

        # Our assumption means the distance from the origin to the center of the eyes and the mouth is the same
        # The origins are also the same, so if lambda is the distance to the face:
        distance = DISTANCE_EYES_MOUTH_VERTICAL / eye_center_mouth_vec.length

        eye_right_kp = camera_observation.keypoints[0]
        eye_left_kp = camera_observation.keypoints[1]
        mouth_kp = camera_observation.keypoints[3]
        nose_kp = camera_observation.keypoints[2]
        eye_center_mouth_pix = (
            eye_right_kp + (eye_left_kp - eye_right_kp) / 2 - mouth_kp
        )
        nose_mouth_vec = nose_kp - mouth_kp

        # Check if the head is pointing left or right by looking at which side the nose point
        # is from the nose -> mouth line

        if WorldFace.aspect_ratio:
            left_right = (
                Vector2(
                    [-nose_mouth_vec.y, nose_mouth_vec.x * WorldFace.aspect_ratio]
                ).dot(
                    Vector2(
                        [
                            eye_center_mouth_pix.x * WorldFace.aspect_ratio,
                            eye_center_mouth_pix.y,
                        ]
                    )
                )
                < 0
            )
        else:
            left_right = False
        eye_distance_norm = (
            eye_right_ray.direction - eye_left_ray.direction
        ).length * distance

        events = (
            camera_observation.face_pose.events
            if camera_observation.face_pose
            else None
        )
        speaking = (
            camera_observation.face_pose.vvad if camera_observation.face_pose else None
        )
        return cls(
            camera_observation,
            distance,
            rays,
            left_right,
            eye_distance_norm,
            center_ray,
            events,
            speaking,
        )


class WorldFace(WorldObject):
    # Maximum number of times to send an image of a face for identification
    MAX_N_SENDS = 10
    ANGLE_UPDATE_MASS = 0.2

    # Default distance between eyes from fronton
    DEFAULT_EYE_EYE_DISTANCE_FRONTON = 0.058
    EYE_EYE_DISTANCE_UPDATE_MASS = 0.02

    TIMEOUT_S = 5
    TIMEOUT_NS = int(TIMEOUT_S * 1e9)

    # Process noise is the varience in acceleration for a face (in m / s ** 2)
    PROCESS_NOISE = 0.1
    SENSOR_NOISE_PERPENDICULAR_NORM = 0.001
    SENSOR_NOISE_DISTANCE_NORM = 0.0005
    INITIAL_POSITION_VAR = 5e-6
    INITIAL_VELOCITY_VAR = 1e-5

    SPEAKING_EXP_MASS = 0.8
    EVENT_COOL_DOWN = 2.5
    CONFIDENCES_LEN = 5  # The length of the confidences stored

    OOF_VELOCITY_DAMPING = (
        0.96  # The velocity damping applied to faces out of frame of view
    )
    _said = None

    aspect_ratio = None

    def __init__(self, id_, position, sample_time_s, saccades, roll, yaw, confidence):
        super().__init__(id_, sample_time_s)
        self.roll = roll
        self.yaw = yaw
        self.speaking = 0
        self.events: List[str] = []
        self.event_cool_down_count = 0

        # Filters
        self.position_filter = KalmanFilter3D(
            position,
            self.PROCESS_NOISE,
            self.SENSOR_NOISE_PERPENDICULAR_NORM,
            self.SENSOR_NOISE_DISTANCE_NORM,
            self.INITIAL_POSITION_VAR,
            self.INITIAL_VELOCITY_VAR,
            sample_time_s,
        )
        self.saccade_filters = [
            KalmanFilter3D(
                saccade,
                self.PROCESS_NOISE,
                self.SENSOR_NOISE_PERPENDICULAR_NORM,
                self.SENSOR_NOISE_DISTANCE_NORM,
                self.INITIAL_POSITION_VAR,
                self.INITIAL_VELOCITY_VAR,
                sample_time_s,
            )
            for saccade in saccades
        ]

        self.distance_eye_eye_fronton = None
        self.server = None

        self.update_coroutine = None
        self.has_spoken = False

        self.info = None
        self.profile_id = None
        self.face_embeddings = []
        self.confidences = deque(maxlen=WorldFace.CONFIDENCES_LEN)
        self.confidences.appendleft(confidence)

        self._entered_event_sent = False
        self._said = None
        self._last_saying_update = None

    @property
    def said(self):
        return self._said

    @said.setter
    def said(self, value):
        self._said = value
        self._last_saying_update = time.time()

    def __del__(self):
        if self._entered_event_sent:
            ROBOT_STATE.interaction_history.add_to_memory(
                INTERACTION_HISTORY.PersonExitEvent(f"Person {self.id}")
            )

    async def cleanup(self):
        if len(self.face_embeddings) > 0:
            try:
                await PROFILES.update_from_conversation(self)
            except Exception:
                pass
        if self.server is not None:
            await self.server.close()

    @classmethod
    def process_observation(
        cls, observation: WorldFaceObservation, eye_eye_distance_fronton=None
    ):
        (
            eye_right_ray,
            eye_left_ray,
            nose_ray,
            mouth_ray,
            ear_right_ray,
            ear_left_ray,
        ) = observation.saccade_rays

        # Assume that pitch is 0. Estimate roll by looking at eye tilt
        eye_eye_vec = eye_left_ray.direction - eye_right_ray.direction
        roll = -atan2(eye_eye_vec[2], Vector2((eye_eye_vec[0], eye_eye_vec[1])).length)

        # Yaw is how far the head is turned left / right. Estimated by looking at distance between eyes compared to distance when face is front on
        if eye_eye_distance_fronton is None:
            cos_yaw = 1
        else:
            cos_yaw = observation.eye_distance_norm / eye_eye_distance_fronton
            if cos_yaw > 1:
                cos_yaw = 1
        yaw = acos(cos_yaw)

        # Fix sign on yaw
        if not observation.left_right:
            yaw *= -1
        sin_yaw = sin(yaw)

        # Get all the visemes in 3D space
        eye_right = eye_right_ray.point(
            observation.estimated_distance + sin_yaw * DISTANCE_EYE_TO_EYE / 2
        )
        eye_left = eye_left_ray.point(
            observation.estimated_distance - sin_yaw * DISTANCE_EYE_TO_EYE / 2
        )
        nose = nose_ray.point(
            observation.estimated_distance - DISTANCE_NOSE_JUT * cos_yaw
        )

        center = nose_ray.point(
            observation.estimated_distance
            - DISTANCE_NOSE_JUT
            + DISTANCE_NOSE_HEAD_BACK / 2
        )
        return (
            (center, nose_ray.direction),
            [
                (eye_right, eye_right_ray.direction),
                (eye_left, eye_left_ray.direction),
                (nose, nose_ray.direction),
            ],
            roll,
            yaw,
        )

    @classmethod
    def from_observation(
        cls,
        observation: WorldFaceObservation,
        sample_time_s,
        id_=None,
        eye_eye_distance_fronton=None,
    ):
        center, saccades, roll, yaw = cls.process_observation(
            observation, eye_eye_distance_fronton
        )
        return cls(
            id_,
            center[0],
            sample_time_s,
            [s[0] for s in saccades],
            roll,
            yaw,
            observation.confidence,
        )

    def update_no_detection(self):
        self.confidences.appendleft(0)

    def update_out_of_frame(self):
        # Decay the velocity
        self.position_filter.velocity_estimate *= self.OOF_VELOCITY_DAMPING
        for filt in self.saccade_filters:
            filt.velocity_estimate *= self.OOF_VELOCITY_DAMPING

    def update(self, world_observation: WorldFaceObservation, sample_time_s: float):
        if self.distance_eye_eye_fronton is None:
            self.distance_eye_eye_fronton = self.DEFAULT_EYE_EYE_DISTANCE_FRONTON

        # When there is a change in face direction (a zero crossing) you know the face is close to front on.
        # Update the front-on eye eye distance
        elif (self.yaw > 0) != world_observation.left_right:
            self.distance_eye_eye_fronton = (
                world_observation.eye_distance_norm * self.EYE_EYE_DISTANCE_UPDATE_MASS
                + self.distance_eye_eye_fronton
                * (1 - self.EYE_EYE_DISTANCE_UPDATE_MASS)
            )

        position, saccades, roll, yaw = self.process_observation(
            world_observation, eye_eye_distance_fronton=self.distance_eye_eye_fronton
        )

        self.position_filter.update(
            position[0], position[1], world_observation.estimated_distance
        )
        [
            filt.update(s[0], s[1], world_observation.estimated_distance)
            for filt, s in zip(self.saccade_filters, saccades)
        ]

        self.yaw = yaw * self.ANGLE_UPDATE_MASS + self.yaw * (
            1 - self.ANGLE_UPDATE_MASS
        )
        self.roll = roll * self.ANGLE_UPDATE_MASS + self.roll * (
            1 - self.ANGLE_UPDATE_MASS
        )

        if world_observation.speaking is not None:
            self.speaking = self.SPEAKING_EXP_MASS * self.speaking + (
                1 - self.SPEAKING_EXP_MASS
            ) * int(world_observation.speaking)

        self.events = world_observation.events
        if self.events and time.time() > self.event_cool_down_count:
            system.messaging.post(
                "non_verbal_interaction_trigger", ", ".join(self.events)
            )
            self.event_cool_down_count = time.time() + self.EVENT_COOL_DOWN
        self.confidences.appendleft(world_observation.confidence)
        super().update(world_observation, sample_time_s)
        if self.observations_to_mature == 0 and not self._entered_event_sent:
            ROBOT_STATE.interaction_history.add_to_memory(
                INTERACTION_HISTORY.PersonEntryEvent(f"Person {self.id}")
            )
            self._entered_event_sent = True

        perception_state.update_face_height(self.position[2])

        if self._last_saying_update and (sample_time_s - self._last_saying_update > 5):
            self._last_saying_update = None
            self.said = None

    def server_task_done_cb(self, *args):
        self.update_coroutine = None

    def add_image(self, image_observation: types.FaceDetection, image: Image):
        if image is not None:
            if (
                (self.observations_to_mature == 0)
                and (len(self.face_embeddings) <= self.MAX_N_SENDS)
                and (self.update_coroutine is None)
                and (self.info is None)
            ):
                image_width, image_height = image.size
                l, t, w, h = image_observation.rect
                left = l * image_width
                top = t * image_height
                right = left + w * image_width
                bottom = top + h * image_height
                image_cropped = image.crop((left, top, right, bottom))

                loop = asyncio.get_event_loop()

                # Update the face in the background
                self.update_coroutine = loop.create_task(
                    self.update_from_image(image_cropped)
                )
                self.update_coroutine.add_done_callback(self.server_task_done_cb)

    async def update_from_image(self, image):
        # Get the face embedding
        face_embedding = await face_embedding_client.get_face_embedding(image)
        if face_embedding is None:
            return None
        self.face_embeddings.append(face_embedding)

        if profiles_client is None:
            return

        if self.info is None:
            resp = await profiles_client.get_profile_from_face_embedding(face_embedding)
            if resp is not None:
                self.info = resp["info"]
                self.profile_id = resp["id"]

    async def save_info(self, info):
        if info is not None:
            if self.profile_id is None:
                if not await profiles_client.add_profile(self.face_embeddings, info):
                    print("FAILED to update info")
            else:
                if not await profiles_client.update_profile_info(self.profile_id, info):
                    print("FAILED to update info")

        else:
            if self.profile_id is not None:
                if not await profiles_client.delete_profile(self.profile_id):
                    print("FAILED to delete profile")
            else:
                assert False, "Attempt to create new profile with no info"
        self.info = info

    @property
    def position(self):
        _position = self.position_filter.position_estimate
        if not isinstance(_position, Point3):
            _position = Point3(_position.elements)
        return _position

    @property
    def confidence(self):
        return sum(self.confidences) / len(self.confidences)

    @property
    def distance(self):
        return sqrt(
            self.position[0] * self.position[0] + self.position[1] * self.position[1]
        )

    @property
    def saccades(self):
        return [s.position_estimate for s in self.saccade_filters]

    @property
    def trans(self):
        rot_to_facing_camera = Matrix4.from_3x3(
            Matrix3.from_z_rotation(pi + atan2(self.position[1], self.position[0]))
        )
        rot_roll = Matrix4.from_3x3(Matrix3.from_x_rotation(self.roll))
        rot_yaw = Matrix4.from_3x3(Matrix3.from_z_rotation(self.yaw))
        trans_center = Matrix4.from_translation(self.position)

        return trans_center @ rot_yaw @ rot_roll @ rot_to_facing_camera

    def to_viz_data(self, sample_time_ns: int):
        if self.info is not None:
            name = self.info.get("name", None)
        else:
            name = None
        return DetectedFace3D(
            self.id,
            self.position,
            self.saccades,
            self.trans,
            sample_time_ns,
            name,
            self.said,
        )

    def predict(self, sample_time):
        self.position_filter.predict(sample_time)

        [filt.predict(sample_time) for filt in self.saccade_filters]

    def likelihood(self, camera_observation):
        """The likelihood that a detected face corresonds to this one."""
        detected_position = camera_observation.center_ray.point(
            camera_observation.estimated_distance
        )
        error = detected_position - self.position_filter.position_estimate
        inv_cov = Matrix3(self.position_filter.var_xx.elements)
        inv_cov.invert_not_orth()
        inv_cov_times_error = inv_cov * error
        exponent = error.dot(inv_cov_times_error) * -0.5
        norm = sqrt(self.position_filter.var_xx.det() * PI_TIMES_2_CUBED)
        return exp(exponent) / norm

    def proxy_likelihood(self, camera_observation):
        """Gaussian PDF is too sensitive... Use distance from point as a proxy instead."""
        detected_position = camera_observation.center_ray.point(
            camera_observation.estimated_distance
        )
        error = (detected_position - self.position_filter.position_estimate).length
        if error < self.SAME_OBJECT_DISTANCE_THRESHOLD_M:
            return (
                self.SAME_OBJECT_DISTANCE_THRESHOLD_M - error
            ) / self.SAME_OBJECT_DISTANCE_THRESHOLD_M
        else:
            return 0

    def joint_probability(self, camera_observation):
        return self.proxy_likelihood(camera_observation) * self.confidence