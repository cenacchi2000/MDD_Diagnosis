"""Match a set of detections of faces to world faces"""

WORLD_FACE_MODULE = system.import_library("./world_face.py")

perception_state = system.import_library("../perception_state.py").perception_state

FACE_SIZE_PIX_NORM = 0.1  # Size of a face in normalised pixels at 1 m
MIN_JOINT_PROB = 0  # Minimum joint_probability probability to consider a face + observation match valid
PROB_NEW_OBSERVATION = 0.01  # The probability of a new face.


def get_probs(sample_time_ns, inverse_converter, world_object_observations):
    # Check which faces are behind other faces so cannot be detected
    face_in_image_locations = {
        face: inverse_converter.convert(face.position, sample_time_ns)
        for face in perception_state.world_faces
    }
    sorted_faces = sorted(perception_state.world_faces, key=lambda face: face.distance)
    overlapped_faces = set()
    for i, face in enumerate(sorted_faces):
        overlap_distance = FACE_SIZE_PIX_NORM / face.distance
        for other_face in sorted_faces[i + 1 :]:
            if (other_face not in overlapped_faces) and (
                (
                    face_in_image_locations[other_face] - face_in_image_locations[face]
                ).length
                < overlap_distance
            ):
                overlapped_faces.add(other_face)

    # Get the probability that each face has been detected
    joint_probs = {face: {} for face in perception_state.world_faces}
    face_observed_probs = {}
    out_of_frame_faces = set()
    for face in perception_state.world_faces:
        if face in overlapped_faces:
            # If the face is overlapped, we reduce the probability that it is detected
            face_observed_probs[face] = 0.1 * face.confidence
        else:
            try:
                x_location, y_location = (
                    face_in_image_locations[face].x,
                    face_in_image_locations[face].y,
                )
            except AttributeError as e:
                log.warning(f"Face location can't be determined: {e}")
                out_of_frame_faces.add(face)
                continue
            min_distance_from_edge = min(
                [
                    x_location,
                    1 - x_location,
                    y_location,
                    1 - y_location,
                ]
            )

            if min_distance_from_edge < 0:
                out_of_frame_faces.add(face)
                continue
            # Reduce the probability that a face is detected if it is close to the edge of the image

            face_observed_probs[face] = face.confidence * max(
                [0, min([0.9, 0.1 + 4 * min_distance_from_edge])]
            )

        for observation_index, detection in enumerate(world_object_observations):
            joint_probability = face.joint_probability(detection)
            if joint_probability > MIN_JOINT_PROB:
                joint_probs[face][observation_index] = joint_probability

    return joint_probs, face_observed_probs, out_of_frame_faces


def get_best_arrangement(
    joint_probs, face_observed_probs, n_observations, out_of_frame_faces
):
    def recurse_best_arrangement(
        faces: set[WORLD_FACE_MODULE.WorldFace],
        observation_indexes: set[int],
        current_arrangement: list[tuple[WORLD_FACE_MODULE.WorldFace,]],
        current_score: float,
        best_arrangement: list[WORLD_FACE_MODULE.WorldFace],
        best_score: float,
    ) -> tuple[list[WORLD_FACE_MODULE.WorldFace], float]:
        """Recursively find the highest probability arrangement of faces and detections.

        Uses the joint_probs and face_observed_probs which have been previously calculated.

        Args:
            faces (set[WorldFace]): the set of faces to match.
            observation_indexes (set[int]): the indexes of each observation which has not yet been paired to a face.
            current_arrangement (list[WorldFace, int]): the current arrangement - a set of (face, observation_index) pairs.
            current_score (float): the current score (analagous to the probability of the arrangement).
            best_arrangement (list[WorldFace]): the current best arrangement.
            best_score (float): the current best score.

        Returns:
            tuple[list[WorldFace, int], float]: the best arrangement, and the best score.
        """
        nonlocal joint_probs, face_observed_probs
        if len(faces) == 0:
            for _ in observation_indexes:
                current_score *= PROB_NEW_OBSERVATION
            if current_score > best_score:
                return current_arrangement, current_score
            else:
                return best_arrangement, best_score
        elif current_score < best_score:
            # Early stop
            return best_arrangement, best_score

        current_face = faces.pop()

        for observation, prob in joint_probs[current_face].items():
            if observation in observation_indexes:
                # Check for each possible match
                current_score_with_detected = (
                    current_score * face_observed_probs[current_face]
                )
                sub_current_arrangement = current_arrangement + [
                    (current_face, observation)
                ]
                sub_observation_indexes = set(
                    [index for index in observation_indexes if index != observation]
                )
                best_arrangement, best_score = recurse_best_arrangement(
                    faces.copy(),
                    sub_observation_indexes,
                    sub_current_arrangement,
                    current_score_with_detected * prob,
                    best_arrangement,
                    best_score,
                )
        # The possibility that this face has not been detected
        sub_current_arrangement = current_arrangement + [(current_face, None)]
        best_arrangement, best_score = recurse_best_arrangement(
            faces.copy(),
            observation_indexes.copy(),
            sub_current_arrangement,
            current_score * (1 - face_observed_probs[current_face]),
            best_arrangement,
            best_score,
        )
        return best_arrangement, best_score

    best_arrangement, _ = recurse_best_arrangement(
        perception_state.world_faces - out_of_frame_faces,
        set(range(n_observations)),
        [],
        1,
        None,
        0,
    )

    return best_arrangement, out_of_frame_faces


def match_observations_to_faces(
    sample_time_ns, converter, world_object_observations
) -> tuple[list[WORLD_FACE_MODULE.WorldFace, int], set[WORLD_FACE_MODULE.WorldFace]]:
    """Match a set of observations in the world reference frame to the set of world faces.

    Args:
        sample_time_s: the time of the observations
        converter: a converter to convert from world observations to the camera reference frame
        world_object_observations: a set of observations in the world reference frame

    Returns:
        the set of matches - a list of world_face, observation_index pairs; and a set of world_faces which are out of frame
    """
    joint_probs, face_observed_probs, out_of_frame_faces = get_probs(
        sample_time_ns,
        converter,
        world_object_observations,
    )
    return get_best_arrangement(
        joint_probs,
        face_observed_probs,
        len(world_object_observations),
        out_of_frame_faces,
    )