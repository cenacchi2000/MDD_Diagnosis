from math import radians
from time import monotonic as now

from ea.math3d import Vector3 as V3
from ea.math3d import (
    to_spherical_position,
    cartesian_to_spherical,
    spherical_to_cartesian,
)
from ea.util.number import clamp
from tritium.world.geom import Point3

contributor = system.import_library("../lib/contributor.py")
"""
Given a look at target. Have the head look at it.
"""
head_yaw = system.control("Head Yaw", "Mesmer Neck 1", acquire=["min", "max"])
head_pitch = system.control("Head Pitch", "Mesmer Neck 1", acquire=["min", "max"])

SELF_IDENTIFIER = "NECK_LOOK_AT"
LOOKAT_CONFIG = system.import_library("../../Config/LookAt.py").CONFIG


def sticky_speed(speed, target, position):
    # Unstick at error angles greater than
    ANGLE = radians(LOOKAT_CONFIG["NECK_STICKY_ANGLE"])
    # Unstick after being stuck for
    SECONDS = LOOKAT_CONFIG["NECK_STICKY_DURATION"]
    self = sticky_speed
    if self.stuck is None:
        if not self.last_position:
            vol = 1
        else:
            vol = abs(position.angle_to(self.last_position))
        self.last_position = position
        probe("sticky_speed.vol", vol)
        if vol < 0.007:
            self.stuck = target
            self.stuck_at = now()
    else:
        if self.stuck.angle_to(target) > ANGLE or self.stuck_at + SECONDS < now():
            self.stuck = self.stuck_at = None
        else:
            # if uniform(0, 100) < 1:
            #     self.stuck.phi = lerp(self.stuck.phi, target.phi, uniform(0.2, 1))
            #     self.stuck.theta = lerp(self.stuck.theta, target.theta, uniform(0.5, 1))
            target = self.stuck
    probe("sticky_speed.stuck", self.stuck)
    return speed, target


sticky_speed.stuck = sticky_speed.stuck_at = sticky_speed.last_position = None


def reduce(speed, target, position):
    yaw = target.phi_degrees
    yaw *= LOOKAT_CONFIG["NECK_YAW_SCALER"]
    yaw = clamp(yaw, LOOKAT_CONFIG["NECK_YAW_MIN"], LOOKAT_CONFIG["NECK_YAW_MAX"])
    target.phi_degrees = yaw
    pitch = target.theta_degrees
    pitch *= LOOKAT_CONFIG["NECK_PITCH_SCALER"]
    pitch = clamp(
        pitch, LOOKAT_CONFIG["NECK_PITCH_MIN"], LOOKAT_CONFIG["NECK_PITCH_MAX"]
    )
    target.theta_degrees = pitch

    target.theta_degrees += LOOKAT_CONFIG["NECK_PITCH_OFFSET"]
    return speed, target


class Activity:
    MODIFIERS = [
        reduce,
        sticky_speed,
    ]
    SPEED = 500
    consumer = None

    def on_start(self):
        self.consumer = contributor.ConsumerRef("look")
        self.look_at_target = Point3([0.5, 0, 1.5])

    def on_message(self, channel, message):
        if self.consumer:
            self.consumer.on_message(channel, message)

    def step_neck(self, target, consumer):
        # Find where the head is currently looking at
        to_spine = consumer.converter("Head", "spine")
        position = to_spine.convert(Point3([1, 0, 0])) - to_spine.convert(
            Point3([0, 0, 0])
        )
        position = cartesian_to_spherical(V3(*position.elements))
        probe("relative pos", position)
        speed = 1
        for modifier in self.MODIFIERS:
            speed, target = modifier(speed, target, position)
        speed = speed * self.SPEED

        target_cartisian = spherical_to_cartesian(target)
        position_cartisian = spherical_to_cartesian(position)

        error = target_cartisian - position_cartisian
        if error.length > speed:
            error.length = speed
            target = position_cartisian + error
        else:
            target = target_cartisian
        target = cartesian_to_spherical(target)
        probe("processed target", target)

        probe("head_yaw.min", head_yaw.min)
        probe("head_yaw.max", head_yaw.max)
        probe("head_pitch.min", head_pitch.min)
        probe("head_pitch.max", head_pitch.max)
        if head_yaw.min is None or head_yaw.max is None:
            return
        else:
            dmd = clamp(target.phi_degrees, head_yaw.min, head_yaw.max)
            if getattr(system.unstable.owner, "mix_pose", None) is not None:
                system.unstable.owner.mix_pose.add_relative(
                    SELF_IDENTIFIER, ("Head Yaw", "Mesmer Neck 1"), dmd
                )
            probe("dmd", dmd)

        if head_pitch.min is None or head_pitch.max is None:
            return
        else:
            dmd_pitch = clamp(target.theta_degrees, head_pitch.min, head_pitch.max)
            if getattr(system.unstable.owner, "mix_pose", None) is not None:
                system.unstable.owner.mix_pose.add_relative(
                    SELF_IDENTIFIER, ("Head Pitch", "Mesmer Neck 1"), dmd_pitch
                )
            probe("dmd_pitch", dmd_pitch)

    @system.tick(fps=20)
    def on_tick(self):
        target, changed, consumer = self.consumer.get_private_target(tag="neck")

        if not target:
            return

        target = consumer.convert(target, "neck_root")
        probe("target", target)
        if not target:
            return

        to_neck = consumer.converter("Head", "neck_root")
        head_base = to_neck.convert(Point3([0, 0, 0]))
        if not head_base:
            return
        target = target - head_base

        sph = to_spherical_position(V3(*target.elements))
        self.step_neck(sph, consumer)
        # print(self.converter._manager._frame_specs.items.values())
        probe("look_at_target", target)