"""Verify an explicitly prescribed collider at the legacy coupling boundary."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        run(args.output)
    except Exception as error:
        (args.output / "failure.json").write_text(json.dumps({
            "error": f"{type(error).__name__}: {error}", "physical_validation": False,
        }, indent=2) + "\n")
        raise


def run(output):
    import genesis as gs
    import numpy as np
    from genesis.utils.misc import qd_to_numpy

    workspace = Path(__file__).resolve().parents[1]
    review = json.loads((workspace / "docs/evidence/genesis-feasibility/source-review.json")
                        .read_text())
    root = Path(gs.__file__).resolve().parent.parent
    for entry in review["files"]:
        if hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Pinned source mismatch: {entry['path']}")
    gs.init(backend=gs.cpu, seed=0, logging_level="warning")
    dt = 0.001
    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=dt, substeps=1, gravity=(0, 0, 0)),
        mpm_options=gs.options.MPMOptions(grid_density=50, particle_size=0.01,
                                          lower_bound=(-0.4, -0.3, -0.1),
                                          upper_bound=(0.4, 0.3, 0.5)),
        coupler_options=gs.options.LegacyCouplerOptions(), show_viewer=False,
    )
    tool = scene.add_entity(gs.morphs.Box(pos=(0, 0, 0.2), size=(0.05, 0.1, 0.1)),
                            material=gs.materials.Rigid(coup_friction=0.5))
    scene.add_entity(gs.morphs.Box(pos=(-0.25, 0, 0.2), size=(0.04, 0.04, 0.04)),
                     material=gs.materials.MPM.Sand(E=1e6, rho=1600, sampler="regular"))
    scene.build()
    coupler = scene.sim.coupler
    original_couple = coupler.couple
    trace = []
    target = {"pos": None, "vel": None}

    def prescribed_couple(frame):
        # Diagnostic boundary condition: discard the freely integrated tool
        # pose and velocity immediately before evaluating material contact.
        tool.set_pos(target["pos"], zero_velocity=False, relative=False)
        tool.set_dofs_velocity([*target["vel"], 0, 0, 0])
        geoms = qd_to_numpy(scene.rigid_solver.dyn_state.geoms.pos)
        links = scene.rigid_solver.dyn_state.links
        pos = np.asarray(geoms[tool.geoms[0].idx]).reshape(3)
        vel = np.asarray(qd_to_numpy(links.cd_vel)[tool.links[0].idx]).reshape(3)
        angular = np.asarray(qd_to_numpy(links.cd_ang)[tool.links[0].idx]).reshape(3)
        if not (np.allclose(pos, target["pos"], rtol=0, atol=1e-7) and
                np.allclose(vel, target["vel"], rtol=0, atol=1e-7) and
                np.allclose(angular, 0, rtol=0, atol=1e-7)):
            raise RuntimeError(f"Collider boundary mismatch: {pos}, {vel}, {angular}")
        original_couple(frame)
        force = -np.asarray(qd_to_numpy(links.cfrc_coupling_vel), dtype=float).reshape(-1, 3)
        if not np.isfinite(force).all() or np.any(force != 0):
            raise RuntimeError("Separated fixture has nonzero or nonfinite coupling force")
        trace.append(dict(command_position_m=target["pos"], command_velocity_m_s=target["vel"],
                          collider_position_m=pos.tolist(), collider_velocity_m_s=vel.tolist(),
                          collider_angular_velocity_rad_s=angular.tolist()))

    coupler.couple = prescribed_couple
    try:
        for step in range(40):
            t = step * dt
            target["pos"] = [0.3 * min(t, 0.02) - 0.3 * max(t - 0.02, 0), 0, 0.2]
            target["vel"] = [0.3 if t < 0.02 else -0.3, 0, 0]
            scene.step()
    finally:
        coupler.couple = original_couple
    if len(trace) != 40:
        raise RuntimeError("Expected one boundary callback per step")
    (output / "record.json").write_text(json.dumps(dict(
        dt_s=dt, trajectory=trace, source_commit=review["commit"],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        physical_validation=False,
        limitation="Separated CPU boundary test only; no loaded contact or actuator qualification",
    ), indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
