"""Experimental fixed-base excavator using the shared coupled world stepping path."""

from dataclasses import replace

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverFeatherstone

from excavation_sim.backends.newton_tool import NewtonToolWorld
from excavation_sim.core import BackendInfo, Capability, JointCommand
from excavation_sim.robots.excavator import add_excavator


def rotate(q, v):
    xyz = np.asarray(q[:3])
    return v + 2 * np.cross(xyz, np.cross(xyz, v) + q[3] * v)


def gravity_compensation(poses, local_com, masses):
    """Negative gravity moment at each revolute pivot for this serial four-link asset."""
    centers = np.array([p[:3] + rotate(p[3:], c) for p, c in zip(poses, local_com, strict=True)])
    torque = np.zeros(4)
    for j in range(4):
        axis = (
            np.array([0.0, 0.0, 1.0]) if j == 0 else rotate(poses[j, 3:], np.array([0.0, 1.0, 0.0]))
        )
        for i in range(j, 4):
            moment = np.cross(centers[i] - poses[j, :3], np.array([0.0, 0.0, -9.81 * masses[i]]))
            torque[j] -= np.dot(moment, axis)
    return torque


@wp.kernel
def measure_material(
    q: wp.array(dtype=wp.vec3),
    mass: wp.array(dtype=float),
    body_q: wp.array(dtype=wp.transform),
    bucket: int,
    result: wp.array(dtype=float),
    dwell: wp.array(dtype=float),
    lifted: wp.array(dtype=int),
    elapsed: float,
):
    i = wp.tid()
    point = q[i]
    local = wp.transform_point(wp.transform_inverse(body_q[bucket]), point)
    if (
        local[0] >= 0.0
        and local[0] <= 0.16
        and wp.abs(local[1]) <= 0.06
        and local[2] >= -0.04
        and local[2] <= 0.06
        and point[2] > 0.22
    ):
        wp.atomic_add(result, 0, mass[i])
        dwell[i] += elapsed
        if dwell[i] >= 0.1:
            lifted[i] = 1
    else:
        dwell[i] = 0.0
    if (
        lifted[i] == 1
        and wp.abs(point[0]) <= 0.25
        and point[1] >= 0.25
        and point[1] <= 0.55
        and point[2] >= -0.04
        and point[2] <= 0.15
    ):
        wp.atomic_add(result, 1, mass[i])


class NewtonExcavatorWorld(NewtonToolWorld):
    info = BackendInfo(
        "newton-excavator",
        "0.1",
        frozenset(
            {
                Capability.GRANULAR_SOIL,
                Capability.REACTION_FORCE,
                Capability.DYNAMIC_TOOL,
                Capability.SURFACE_OBSERVATION,
            }
        ),
        (
            "Procedural bench-scale machine; not physically validated",
            "Experimental lagged coupling",
            "No hydraulic model",
            "Ideal sensors; no exact restart",
        ),
    )

    def _rigid_solver(self, model):
        return SolverFeatherstone(model)

    def _add_robot(self, builder):
        self.asset = add_excavator(builder)
        builder.joint_q[:] = self.asset.initial_q
        return list(self.asset.bodies), list(self.asset.joints), self.asset.bucket_body

    def _initialize_state(self):
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.state)
        self._target_q = np.asarray(self.asset.initial_q).copy()
        self._torque = np.zeros(4)
        self._positive_work = 0.0
        self._material_metrics = wp.zeros(2, dtype=float)
        self._lift_dwell = wp.zeros(self.model.particle_count, dtype=float)
        self._ever_lifted = wp.zeros(self.model.particle_count, dtype=int)
        self._metrics_tick = 0
        self._masses = self.model.body_mass.numpy().astype(np.float64)
        self._com = self.model.body_com.numpy().astype(np.float64)

    def _observation(self):
        observation = super()._observation()
        return replace(
            observation,
            joint_position_rad=tuple(map(float, self.state.joint_q.numpy()[:4])),
            joint_velocity_rad_s=tuple(map(float, self.state.joint_qd.numpy()[:4])),
        )

    def _command_forces(self, command: JointCommand):
        if not isinstance(command, JointCommand):
            raise TypeError("excavator requires a JointCommand")
        return np.zeros((self.model.body_count, 6), dtype=np.float32)

    def _substep_forces(self, command, buffer):
        q, qd = self.state.joint_q.numpy()[:4], self.state.joint_qd.numpy()[:4]
        requested_velocity = np.asarray(command.velocity_targets) * 0.6
        self._target_q = np.clip(
            self._target_q + requested_velocity * self.clock.dt_s,
            self.asset.lower_limits_rad,
            self.asset.upper_limits_rad,
        )
        gravity = gravity_compensation(self.state.body_q.numpy(), self._com, self._masses)
        desired = 120 * (self._target_q - q) + 12 * (requested_velocity - qd) + gravity
        limits = np.asarray(self.asset.effort_limits_nm)
        desired = np.clip(desired, -limits, limits)
        # First-order motor effort response, updated each physics tick. No hydraulic claim.
        alpha = 1 - np.exp(-self.clock.dt_s / 0.05)
        self._torque += alpha * (desired - self._torque)
        self._positive_work += float(np.maximum(self._torque * qd, 0).sum()) * self.clock.dt_s
        efforts = np.zeros(self.model.joint_dof_count, dtype=np.float32)
        efforts[:4] = self._torque
        self.control.joint_f.assign(efforts)
        self._actuator = np.zeros(3)
        return np.zeros((self.model.body_count, 6), dtype=np.float32)

    def diagnostics(self):
        self._require_ready()
        if self.tick == self._metrics_tick:
            values = self._material_metrics.numpy()
        else:
            self._update_material_metrics()
            values = self._material_metrics.numpy()
        return replace(
            super().diagnostics(),
            actuator_torque_nm=tuple(map(float, self._torque)),
            lifted_bucket_mass_kg=float(values[0]),
            deposited_mass_kg=float(values[1]),
            positive_actuator_work_j=self._positive_work,
        )

    def runtime_metadata(self):
        return {
            **super().runtime_metadata(),
            "machine_asset": "procedural-excavator-v2",
            "joint_order": ["slew", "boom", "stick", "bucket"],
            "joint_lower_limits_rad": list(self.asset.lower_limits_rad),
            "joint_upper_limits_rad": list(self.asset.upper_limits_rad),
            "effort_limits_nm": list(self.asset.effort_limits_nm),
            "commanded_velocity_limit_rad_s": 0.6,
            "actuator_response_time_s": 0.05,
            "actuator_update_dt_s": self.clock.dt_s,
            "controller": "PD velocity-target tracking with self-weight gravity compensation",
        }

    def _update_material_metrics(self):
        self._material_metrics.zero_()
        if self.model.particle_count:
            wp.launch(
                measure_material,
                dim=self.model.particle_count,
                inputs=[
                    self.state.particle_q,
                    self.model.particle_mass,
                    self.state.body_q,
                    self.body,
                    self._material_metrics,
                    self._lift_dwell,
                    self._ever_lifted,
                    (self.tick - self._metrics_tick) * self.clock.dt_s,
                ],
                device=self.device,
            )
        self._metrics_tick = self.tick
