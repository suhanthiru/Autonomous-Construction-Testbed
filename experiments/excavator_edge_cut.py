"""Task-space approach, cut, curl, lift, slew, and dump using public geometry."""

import math

from excavation_sim.core import JointCommand


def joints(x, z, pitch, yaw=0.0):
    horizontal, down = x + 0.65, 0.35 - z
    cosine = (horizontal**2 + down**2 - 0.4**2 - 0.35**2) / (2 * 0.4 * 0.35)
    if not -1 <= cosine <= 1:
        raise ValueError("scripted waypoint is outside arm reach")
    stick = math.acos(cosine)
    boom = math.atan2(down, horizontal) - math.atan2(
        0.35 * math.sin(stick), 0.4 + 0.35 * math.cos(stick)
    )
    return yaw, boom, stick, pitch - boom - stick


def blend(a, b, alpha):
    alpha = max(0.0, min(1.0, alpha))
    return tuple(x + (y - x) * alpha for x, y in zip(a, b, strict=True))


class ExcavatorPolicy:
    def reset(self, seed):
        self.seed = seed

    def act(self, observation):
        if not observation.sensor_valid:
            return JointCommand((0.0, 0.0, 0.0, 0.0))
        t = observation.time_s
        waypoints = [
            (0.0, (0.008, 0.374, 0.0, 0.0)),
            (3.0, (-0.18, 0.28, 0.0, 0.0)),
            (6.0, (-0.18, 0.15, 0.8, 0.0)),
            (10.0, (0.02, 0.13, 0.7, 0.0)),
            (14.0, (0.02, 0.16, -0.9, 0.0)),
            (18.0, (0.0, 0.40, -0.9, 0.0)),
            (21.0, (0.0, 0.40, -0.9, 0.6)),
            (25.0, (0.0, 0.40, 0.7, 0.6)),
            (27.0, (0.0, 0.40, 0.7, 0.6)),
        ]
        pose = waypoints[-1][1]
        for (ta, a), (tb, b) in zip(waypoints, waypoints[1:], strict=False):
            if ta <= t <= tb:
                pose = blend(a, b, (t - ta) / (tb - ta))
                break
        target = joints(*pose)
        command = tuple(
            max(-0.7, min(0.7, 3 * (goal - current)))
            for goal, current in zip(target, observation.joint_position_rad, strict=True)
        )
        return JointCommand(command)
