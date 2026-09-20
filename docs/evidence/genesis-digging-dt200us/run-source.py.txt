"""Prescribed box digging in Genesis; numerical comparison, not physical validation."""

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dt", type=float, default=0.0004)
    parser.add_argument("--voxel", type=float, default=0.04)
    parser.add_argument("--spacing", type=float, default=0.02)
    parser.add_argument("--backend", choices=("cpu", "gpu"), default="gpu")
    args = parser.parse_args()
    for value in (args.dt, args.voxel, args.spacing):
        if not math.isfinite(value) or value <= 0:
            parser.error("Discretization values must be finite and positive")
    for interval in (1.2, 0.8, 0.02):
        if not math.isclose(round(interval / args.dt) * args.dt, interval):
            parser.error("Timestep must divide duration, reversal time and force window")
    for extent in (0.4, 0.2):
        if not math.isclose(round(extent / args.spacing) * args.spacing, extent):
            parser.error("Particle spacing must divide bed dimensions")
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        run(args)
    except Exception as error:
        (args.output / "failure.json").write_text(json.dumps(dict(
            error=f"{type(error).__name__}: {error}", physical_validation=False,
        ), indent=2) + "\n")
        raise


def run(args):
    import genesis as gs
    import numpy as np
    from genesis.utils.misc import qd_to_numpy

    script = Path(__file__)
    script_hash = hashlib.sha256(script.read_bytes()).hexdigest()
    review = json.loads((script.resolve().parents[1] /
                        "docs/evidence/genesis-feasibility/source-review.json").read_text())
    package_root = Path(gs.__file__).resolve().parent.parent
    for entry in review["files"]:
        digest = hashlib.sha256((package_root / entry["path"]).read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise RuntimeError(f"Pinned source mismatch: {entry['path']}")
    gs.init(backend=gs.gpu if args.backend == "gpu" else gs.cpu, seed=0, logging_level="warning")
    offset = args.voxel / 2
    lower, upper = (-0.6, -0.6, -0.2), (0.6, 0.6, 0.8)
    gravity = (0, 0, -9.81)
    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=args.dt, substeps=1, gravity=gravity),
        mpm_options=gs.options.MPMOptions(grid_density=1 / args.voxel,
                                          particle_size=args.spacing,
                                          lower_bound=lower, upper_bound=upper),
        coupler_options=gs.options.LegacyCouplerOptions(), show_viewer=False,
    )
    scene.add_entity(gs.morphs.Plane(pos=(0, 0, offset)),
                     material=gs.materials.Rigid(coup_friction=0.5, coup_softness=0.002))
    tool = scene.add_entity(
        gs.morphs.Box(pos=(offset, offset, 0.35 + offset), size=(0.12, 0.12, 0.08)),
        material=gs.materials.Rigid(coup_friction=0.5, coup_softness=0.002),
    )
    material = dict(E=1e6, nu=0.3, rho=1600, friction_angle=math.degrees(math.atan(0.6)),
                    sampler="regular")
    soil = scene.add_entity(
        gs.morphs.Box(pos=(offset, offset, 0.1 + offset), size=(0.4, 0.4, 0.2)),
        material=gs.materials.MPM.Sand(**material),
    )
    scene.build()
    if scene.sim.substeps != 1:
        raise RuntimeError("One substep is required for impulse sampling")
    scale = float(scene.mpm_solver.particle_volume_scale)
    masses = scene.mpm_solver.particles_info.mass.to_numpy().astype(np.float64).reshape(-1) / scale
    if len(masses) != soil.n_particles or not np.all(masses > 0):
        raise RuntimeError("Unexpected particle mass layout")
    if not np.isclose(masses.sum(), 51.2, rtol=1e-5, atol=0):
        raise RuntimeError(f"Bed physical mass differs: {masses.sum()}")
    gravity_impulse = masses.sum() * np.asarray(gravity) * args.dt

    def momentum():
        velocity = soil.get_particles_vel().detach().cpu().numpy().reshape(-1, 3)
        return (masses[:, None] * velocity).sum(axis=0)

    initial = previous = momentum()
    trace = []
    target = {}
    original_couple = scene.sim.coupler.couple

    def prescribed_couple(frame):
        tool.set_pos(target["pos"], zero_velocity=False, relative=False)
        tool.set_quat([1, 0, 0, 0], zero_velocity=False)
        tool.set_dofs_velocity([0, 0, target["vz"], 0, 0, 0])
        state = scene.rigid_solver.dyn_state
        position = np.asarray(qd_to_numpy(state.geoms.pos)[tool.geoms[0].idx]).reshape(3)
        velocity = np.asarray(qd_to_numpy(state.links.cd_vel)[tool.links[0].idx]).reshape(3)
        angular = np.asarray(qd_to_numpy(state.links.cd_ang)[tool.links[0].idx]).reshape(3)
        quat = np.asarray(qd_to_numpy(state.geoms.quat)[tool.geoms[0].idx]).reshape(4)
        if not (np.allclose(position, target["pos"], rtol=0, atol=1e-7) and
                np.allclose(velocity, [0, 0, target["vz"]], rtol=0, atol=1e-7) and
                np.allclose(angular, 0, rtol=0, atol=1e-7) and
                min(np.linalg.norm(quat - [1, 0, 0, 0]),
                    np.linalg.norm(quat + [1, 0, 0, 0])) <= 1e-7):
            raise RuntimeError("Prescribed collider state differs at contact evaluation")
        original_couple(frame)
        force = -np.asarray(qd_to_numpy(state.links.cfrc_coupling_vel), dtype=float)
        force = force.reshape(-1, 3)
        trace.append(dict(command_position_m=list(target["pos"]),
                          command_velocity_m_s=[0, 0, target["vz"]],
                          collider_position_m=position.tolist(),
                          collider_velocity_m_s=velocity.tolist(),
                          collider_quaternion_wxyz=quat.tolist(),
                          tool_reaction_impulse_n_s=(force[tool.links[0].idx] * args.dt).tolist(),
                          all_reaction_impulse_n_s=(force.sum(axis=0) * args.dt).tolist()))

    scene.sim.coupler.couple = prescribed_couple
    steps = round(1.2 / args.dt)
    try:
        for tick in range(steps):
            t = tick * args.dt
            target["pos"] = [offset, offset,
                             0.35 - 0.3 * min(t, 0.8) + 0.3 * max(t - 0.8, 0) + offset]
            target["vz"] = -0.3 if tick < round(0.8 / args.dt) else 0.3
            scene.step()
            if len(trace) != tick + 1:
                raise RuntimeError("Expected one contact callback per step")
            current = momentum()
            residual = current - previous - gravity_impulse + trace[-1]["all_reaction_impulse_n_s"]
            pos = soil.get_particles_pos().detach().cpu().numpy().reshape(-1, 3)
            if not all(np.isfinite(v).all() for v in (current, residual, pos)):
                raise RuntimeError(f"Nonfinite state at step {tick + 1}")
            if not np.all(soil.get_particles_active().detach().cpu().numpy()):
                raise RuntimeError("Unexpected particle deactivation")
            # Keep particles away from the numerical domain boundary, which
            # has no instrumented reaction in this diagnostic.
            if np.any(pos < np.asarray(lower) + 3 * args.voxel) or np.any(
                    pos > np.asarray(upper) - 3 * args.voxel):
                raise RuntimeError("Particles reached the domain safety margin")
            trace[-1].update(time_s=(tick + 1) * args.dt, momentum_kg_m_s=current.tolist(),
                             gravity_impulse_n_s=gravity_impulse.tolist(),
                             unaccounted_momentum_n_s=residual.tolist(),
                             position_min_m=pos.min(axis=0).tolist(),
                             position_max_m=pos.max(axis=0).tolist())
            previous = current
            if (tick + 1) % 250 == 0:
                print({"completed_steps": tick + 1, "total_steps": steps}, flush=True)
    finally:
        scene.sim.coupler.couple = original_couple
    window = round(0.02 / args.dt)
    impulses = [row["tool_reaction_impulse_n_s"][2] for row in trace]
    means = [sum(impulses[i:i + window]) / 0.02 for i in range(0, steps, window)]
    record = dict(dt_s=args.dt, voxel_m=args.voxel, spacing_m=args.spacing,
                  backend=args.backend, material=material, world_offset_m=[offset] * 3,
                  coupling_softness_m=0.002, coupling_friction=0.5,
                  domain_lower_m=lower, domain_upper_m=upper, mass_scale=scale,
                  particle_count=len(masses), physical_mass_kg=float(masses.sum()),
                  initial_momentum_kg_m_s=initial.tolist(), trajectory=trace,
                  tool_vertical_impulse_n_s=sum(impulses), peak_20ms_mean_n=max(means),
                  script_sha256=script_hash,
                  script_changed=script_hash != hashlib.sha256(script.read_bytes()).hexdigest(),
                  source_commit=review["commit"], physical_validation=False,
                  packages={name: importlib.metadata.version(name) for name in
                            ("genesis-world", "torch", "quadrants", "numpy")},
                  limitation=("Unprepared numerical fixture with prescribed collider; "
                              "constitutive equivalence to Newton is not established"))
    (args.output / "record.json").write_text(json.dumps(record,indent=2,allow_nan=False) + "\n")
    if record["script_changed"]:
        raise RuntimeError("Diagnostic source changed during execution")
    print({k: record[k] for k in ("tool_vertical_impulse_n_s", "peak_20ms_mean_n")}, flush=True)


if __name__ == "__main__":
    main()
