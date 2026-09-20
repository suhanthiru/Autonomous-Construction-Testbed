"""Measure Genesis coupling impulse against particle momentum; no physical pass."""

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", choices=("free", "contact"), required=True)
    parser.add_argument("--backend", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--dt", type=float, default=0.0001)
    parser.add_argument("--duration", type=float, default=0.04)
    args = parser.parse_args()
    if not all(math.isfinite(v) and v > 0 for v in (args.dt, args.duration)):
        parser.error("duration and timestep must be finite and positive")
    steps = round(args.duration / args.dt)
    if steps < 1 or not math.isclose(steps * args.dt, args.duration):
        parser.error("duration must contain an integer number of steps")
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        run(args, steps)
    except Exception as error:
        (args.output / "failure.json").write_text(json.dumps({
            "error": f"{type(error).__name__}: {error}", "physical_validation": False,
        }, indent=2) + "\n")
        raise


def run(args, steps):
    import genesis as gs
    import numpy as np
    from genesis.utils.misc import qd_to_numpy

    if importlib.metadata.version("genesis-world") != "1.4.0":
        raise RuntimeError("This private-field diagnostic requires Genesis 1.4.0")
    workspace = Path(__file__).resolve().parents[1]
    reviewed = json.loads((workspace / "docs/evidence/genesis-feasibility/source-review.json")
                          .read_text())
    package_root = Path(gs.__file__).resolve().parent.parent
    for entry in reviewed["files"]:
        digest = hashlib.sha256((package_root / entry["path"]).read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise RuntimeError(f"Reviewed source differs: {entry['path']}")

    gs.init(backend=gs.cpu if args.backend == "cpu" else gs.gpu, seed=0,
            logging_level="warning")
    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=args.dt, substeps=1, gravity=(0, 0, 0)),
        mpm_options=gs.options.MPMOptions(grid_density=50, particle_size=0.01,
                                          lower_bound=(-0.4, -0.3, -0.1),
                                          upper_bound=(0.4, 0.3, 0.5)),
        coupler_options=gs.options.LegacyCouplerOptions(), show_viewer=False,
    )
    wall_x = 0.0 if args.case == "contact" else 0.25
    scene.add_entity(gs.morphs.Box(pos=(wall_x, 0, 0.2), size=(0.05, 0.2, 0.2), fixed=True),
                     material=gs.materials.Rigid(coup_friction=0.5))
    soil = scene.add_entity(
        gs.morphs.Box(pos=(-0.1, 0, 0.2), size=(0.08, 0.08, 0.08)),
        material=gs.materials.MPM.Sand(E=1e6, nu=0.3, rho=1600,
                                       friction_angle=30, sampler="regular"),
    )
    scene.build()
    if scene.sim.substeps != 1:
        raise RuntimeError("Force accounting requires one measured substep")
    scale = float(scene.mpm_solver.particle_volume_scale)
    masses = scene.mpm_solver.particles_info.mass.to_numpy().astype(np.float64) / scale
    masses = masses.reshape(-1)
    if len(masses) != soil.n_particles or not np.all(masses > 0):
        raise RuntimeError("Unexpected particle mass layout")
    public_mass = float(soil.get_mass().detach().cpu().numpy().sum())
    if not np.isclose(masses.sum(), public_mass, rtol=1e-5, atol=0):
        raise RuntimeError("Physical mass disagrees with public mass query")

    def momentum():
        vel = soil.get_particles_vel().detach().cpu().numpy().reshape(-1, 3)
        return (masses[:, None] * vel).sum(axis=0)

    def reaction():
        stored = qd_to_numpy(scene.rigid_solver.dyn_state.links.cfrc_coupling_vel)
        return -np.asarray(stored, dtype=np.float64).reshape(-1, 3).sum(axis=0) * args.dt

    # Velocity setters are applied during stepping. Exclude this commanded
    # initialization step and retain its resulting state as the audit origin.
    soil.set_particles_vel((1, 0, 0))
    scene.step()
    initial = previous = momentum()
    initial_reaction = reaction()
    trace = []
    for tick in range(steps):
        scene.step()
        current, impulse = momentum(), reaction()
        residual = current - previous + impulse
        pos = soil.get_particles_pos().detach().cpu().numpy().reshape(-1, 3)
        active = soil.get_particles_active().detach().cpu().numpy()
        if not all(np.isfinite(v).all() for v in (current, impulse, residual, pos)):
            raise RuntimeError(f"Nonfinite state at step {tick + 1}")
        if not np.all(active):
            raise RuntimeError("Particle deactivation invalidates this closed accounting fixture")
        trace.append(dict(time_s=(tick + 1) * args.dt, momentum_kg_m_s=current.tolist(),
                          reaction_impulse_n_s=impulse.tolist(),
                          unaccounted_momentum_n_s=residual.tolist(),
                          position_min_m=pos.min(axis=0).tolist(),
                          position_max_m=pos.max(axis=0).tolist()))
        previous = current
        if (tick + 1) % 100 == 0:
            print({"completed_steps": tick + 1, "total_steps": steps}, flush=True)
    record = dict(case=args.case, backend=args.backend, dt_s=args.dt, steps=steps,
                  particle_count=len(masses), physical_mass_kg=float(masses.sum()),
                  mass_scale=scale, initial_momentum_kg_m_s=initial.tolist(),
                  excluded_initialization_impulse_n_s=initial_reaction.tolist(),
                  trajectory=trace, physical_validation=False,
                  limitation="Diagnostic only; domain-boundary effects and convergence unqualified",
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output / "record.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
