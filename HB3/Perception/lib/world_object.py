from abc import abstractmethod


class WorldObjectObservation:
    pass


class WorldObject:
    # Amount of time since last detection after which the object is timed out
    TIMEOUT_S = 5
    TIMEOUT_NS = int(TIMEOUT_S * 1e9)

    # Minimum number of observations before the object is viewed
    MIN_N_OBSERVATIONS = 10

    # Distance between two objects to indicate they are the same
    SAME_OBJECT_DISTANCE_THRESHOLD_M = 0.6

    def __init__(self, id_, sample_time_s):
        self.id = id_
        self.last_update_time = sample_time_s
        self.observations_to_mature = self.MIN_N_OBSERVATIONS

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if isinstance(other, int):
            return self.id == other
        else:
            return self.id == other.id

    @abstractmethod
    def from_observation(self, observation: WorldObjectObservation):
        pass

    @abstractmethod
    def distance_to(self, camera_observation):
        return (
            self.position
            - camera_observation.center_ray.point(camera_observation.estimated_distance)
        ).length

    @abstractmethod
    def update(self, world_observation, sample_time_s: float):
        self.last_update_time = sample_time_s
        if self.observations_to_mature > 0:
            self.observations_to_mature -= 1