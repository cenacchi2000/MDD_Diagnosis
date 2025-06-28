from math import sqrt

import numpy as np
from tritium.world.geom import Matrix3, Vector3


class KalmanFilter1D:
    """Kalman filter implementation.
    Assumes:
    * Constant velocity
    * Models acceleration as normally distributed about 0 with varience of `process_noise`
    """

    def __init__(
        self,
        initial_position_measurement,
        process_noise,
        var_xx_init,
        var_yy_init,
        start_time,
    ):
        self.process_noise = process_noise

        self.position_estimate = initial_position_measurement
        self.velocity_estimate = 0

        # Initial covarience matrix
        self.var_xx = var_xx_init
        self.cov_xy = 0
        self.var_yy = var_yy_init

        self.last_sample_time = start_time

    def predict(self, sample_time_s):
        delta_t = sample_time_s - self.last_sample_time
        delta_t_2 = delta_t * delta_t
        delta_t_3 = delta_t_2 * delta_t
        delta_t_4 = delta_t_3 * delta_t
        self.last_sample_time = sample_time_s
        # Update position estimate
        self.position_estimate += self.velocity_estimate * delta_t

        # Update covarience estimates
        self.var_xx += (
            self.process_noise * (delta_t_4 / 4)
            + self.cov_xy * (2 * delta_t)
            + self.var_yy * (delta_t * delta_t)
        )
        self.cov_xy += self.process_noise * (delta_t_3 / 2) + self.var_yy * delta_t
        self.var_yy += self.process_noise * delta_t_2

    def update(self, measured_position, measurement_noise):
        denom = 1 / (self.var_xx + measurement_noise)
        lam = denom * (measured_position - self.position_estimate)

        # Update position estimate from new measurement
        self.position_estimate += lam * self.var_xx
        self.velocity_estimate += lam * self.cov_xy

        # Update covarience estimates
        self.var_yy -= denom * self.cov_xy * self.cov_xy
        self.cov_xy -= denom * self.var_xx * self.cov_xy
        self.var_xx -= denom * self.var_xx * self.var_xx

    def step(self, measured_position, delta_t):
        self.predict(delta_t)
        self.update(measured_position)


class KalmanFilter3D:
    """A convenience class for running 3 1d filters on a Point3."""

    def __init__(
        self,
        initial_position_measurement,
        process_noise,
        measurement_noise_perpendicular_norm,
        measurement_noise_radial_norm,  # Distance measurements are less accurate. Seperate them out here
        var_xx_init,
        var_yy_init,
        start_time,
    ):
        self.measurement_noise_perpendicular_norm = measurement_noise_perpendicular_norm
        self.measurement_noise_radial_norm = measurement_noise_radial_norm
        self.process_noise = Matrix3.identity() * process_noise

        self.position_estimate = initial_position_measurement
        self.velocity_estimate = Vector3([0, 0, 0])

        # Initial covarience matrix
        self.var_xx = Matrix3.identity() * var_xx_init
        self.cov_xy = Matrix3.identity() * 0
        self.var_yy = Matrix3.identity() * var_yy_init

        self.last_sample_time = start_time

    def predict(self, sample_time_s):
        delta_t = sample_time_s - self.last_sample_time
        delta_t_2 = delta_t * delta_t
        delta_t_3 = delta_t_2 * delta_t
        delta_t_4 = delta_t_3 * delta_t
        self.last_sample_time = sample_time_s
        # Update position estimate
        self.position_estimate += self.velocity_estimate * delta_t

        # Update covarience estimates
        self.var_xx += (
            self.process_noise * (delta_t_4 / 4)
            + self.cov_xy * (2 * delta_t)
            + self.var_yy * delta_t_2
        )
        self.cov_xy += self.process_noise * (delta_t_3 / 2) + self.var_yy * delta_t
        self.var_yy += self.process_noise * delta_t_2

    def get_pos_cov_matrix(self, direction_vec, distance):
        # Convert the convarience matrix from the direction vector to the standard world coordinate system

        # Precalculate some useful variables
        a, b, c = direction_vec.elements
        a_2 = a * a
        b_2 = b * b

        # Radial variance scales with r**3 (this is an approximation, but correlates to experiments), perpendicular variance scales with r**2 (assuming constant angular variance)
        t = self.measurement_noise_perpendicular_norm * distance**2
        r = self.measurement_noise_radial_norm * distance**3
        if not np.isclose(c, 0):
            c_2 = c * c
            a_c = a / c
            a_c_2 = a_c * a_c
            a_c_2p1 = 1 + a_c_2
            b_2m1 = b_2 - 1

            m = 1 / sqrt(a_c_2p1)
            tm_2 = t * m * m

            # Calculate the matrix elements
            r_00 = r * a_2 + tm_2 * (1 + b_2 * a_c_2)
            r_01 = r * a * b - tm_2 * a * b * a_c_2p1
            r_02 = r * a * c + tm_2 * a_c * b_2m1
            r_11 = r * b_2 + tm_2 * c_2 * a_c_2p1 * a_c_2p1
            r_12 = r * b * c - tm_2 * b * c * a_c_2p1
            r_22 = r * c_2 + tm_2 * (a_c_2p1 + b_2m1)
        else:
            r_00 = r * a_2 + t * b_2
            r_01 = (r - t) * a * b
            r_02 = 0
            r_11 = r * b_2 + t * a_2
            r_12 = 0
            r_22 = t

        return Matrix3([[r_00, r_01, r_02], [r_01, r_11, r_12], [r_02, r_12, r_22]])

    def update(self, measured_positions, direction_vec, dist):
        measurement_noise = self.get_pos_cov_matrix(direction_vec, dist)

        denom = self.var_xx + measurement_noise
        denom.invert_not_orth()
        innovation = measured_positions - self.position_estimate

        # Update position estimate from new measurement
        self.position_estimate += self.var_xx @ denom @ innovation
        self.velocity_estimate += self.cov_xy @ denom @ innovation

        # Update covarience estimates
        self.var_yy -= self.cov_xy @ denom @ self.cov_xy
        self.cov_xy -= self.var_xx @ denom @ self.cov_xy
        self.var_xx -= self.var_xx @ denom @ self.var_xx

    def step(self, measured_position, delta_t, direction_vec, dist):
        self.predict(delta_t)
        self.update(measured_position, direction_vec, dist)