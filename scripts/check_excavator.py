"""Empty-machine integration fixture; not an excavator physical validation."""

import json
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverXPBD

from excavation_sim.backends.newton_tool import NewtonToolWorld, ToolWorldConfig
from excavation_sim.provenance import source_identity
from excavation_sim.robots.excavator import add_excavator


def main():
    # Configure the supported CUDA runtime/cache without constructing a tool world.
    runtime = NewtonToolWorld(ToolWorldConfig(with_soil=False))
    identity = source_identity(Path.cwd())
    with wp.ScopedDevice(runtime.device):
        builder = newton.ModelBuilder()
        asset = add_excavator(builder)
        builder.add_ground_plane()
        model = builder.finalize()
        state, output = model.state(), model.state()
        model.joint_q.assign(np.asarray(asset.initial_q, dtype=np.float32))
        newton.eval_fk(model, model.joint_q, model.joint_qd, state)
        solver = SolverXPBD(model, iterations=20)
        control = model.control()
        pipeline = newton.CollisionPipeline(model, soft_contact_max=0)
        contacts = pipeline.contacts()
        trace = []
        target = np.asarray(asset.initial_q)
        for tick in range(400):
            newton.eval_ik(model, state, state.joint_q, state.joint_qd)
            q, qd = state.joint_q.numpy(), state.joint_qd.numpy()
            torque = np.clip(
                120 * (target - q) - 12 * qd,
                -np.asarray(asset.effort_limits_nm),
                asset.effort_limits_nm,
            )
            control.joint_f.assign(torque.astype(np.float32))
            state.clear_forces()
            pipeline.collide(state, contacts)
            solver.step(state, output, control, contacts, 0.0025)
            state, output = output, state
            if tick % 20 == 0:
                if not np.isfinite(state.body_q.numpy()).all():
                    raise RuntimeError("nonfinite articulation")
                trace.append(
                    {
                        "time_s": (tick + 1) * 0.0025,
                        "joint_q_rad": q.tolist(),
                        "torque_nm": torque.tolist(),
                        "body_poses": state.body_q.numpy().tolist(),
                    }
                )
        report = {
            "status": "executed empty-machine fixture; not physically validated",
            "source": identity,
            "body_mass_kg": model.body_mass.numpy().tolist(),
            "trace": trace,
            "final_joint_error_rad": (q - target).tolist(),
        }
        output_path = Path("runs/excavator-empty.json")
        with output_path.open("x") as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps(report["final_joint_error_rad"]))


if __name__ == "__main__":
    main()
