"""Isolate soil/contact timestep sensitivity under identical prescribed box motion."""

import argparse
import hashlib
import io
import json
import re
from contextlib import redirect_stdout
from math import ceil, isfinite
from pathlib import Path
from time import perf_counter

import newton
import numpy as np
import warp as wp
from newton.solvers import SolverImplicitMPM

from excavation_sim.actuation import ticks_per_update
from excavation_sim.analysis import windowed_force
from excavation_sim.provenance import environment_info, source_identity


def run(dt, voxel=0.04, spacing=0.02, air_drag=1.0, young_modulus=1e15,
        iterations=100, tolerance=1e-5, solver_diagnostics=False, integration_scheme="pic",
        grid_type="fixed", max_active_cells=1 << 18, rebuildable_sparse=False,
        warmstart_mode="auto", world_offset=(0.0, 0.0, 0.0), progress=None,
        collider_basis="S2", momentum_audit=False, settle_s=0.0, settle_dt=0.0025):
    if collider_basis not in ("S2", "Q1", "pic"):
        raise ValueError("unsupported diagnostic collider basis")
    if rebuildable_sparse and grid_type != "sparse":
        raise ValueError("rebuildable sparse requires the sparse grid")
    if len(world_offset) != 3 or not all(isfinite(v) for v in world_offset):
        raise ValueError("world offset must contain three finite coordinates")
    ox, oy, oz = world_offset
    steps = ticks_per_update(dt, 1.2)
    ticks_per_update(dt, 0.02)
    builder = newton.ModelBuilder()
    SolverImplicitMPM.register_custom_attributes(builder)
    body = builder.add_body(
        is_kinematic=True, xform=wp.transform(wp.vec3(ox, oy, 0.35 + oz), wp.quat_identity())
    )
    builder.add_shape_box(
        body,
        hx=0.06,
        hy=0.06,
        hz=0.04,
        cfg=newton.ModelBuilder.ShapeConfig(density=0, mu=0.5),
    )
    builder.add_ground_plane(height=oz)
    dims = [ticks_per_update(spacing, extent) for extent in (0.4, 0.4, 0.2)]
    builder.add_particle_grid(
        pos=wp.vec3(-0.2 + spacing / 2 + ox, -0.2 + spacing / 2 + oy, spacing / 2 + oz),
        rot=wp.quat_identity(),
        vel=wp.vec3(0),
        dim_x=dims[0],
        dim_y=dims[1],
        dim_z=dims[2],
        cell_x=spacing,
        cell_y=spacing,
        cell_z=spacing,
        mass=1600 * spacing**3,
        jitter=0,
        radius_mean=spacing / 2,
        custom_attributes={"mpm:friction": 0.6, "mpm:young_modulus": young_modulus},
    )
    model = builder.finalize()
    cfg = SolverImplicitMPM.Config()
    cfg.voxel_size = voxel
    cfg.grid_type = grid_type
    cfg.grid_padding = 0 if rebuildable_sparse else ceil(0.4 / voxel)
    cfg.max_active_cell_count = max_active_cells
    cfg.max_iterations = iterations
    cfg.tolerance = tolerance
    cfg.air_drag = air_drag
    cfg.strain_basis = "P0"
    cfg.critical_fraction = 0.0
    cfg.integration_scheme = integration_scheme
    cfg.warmstart_mode = warmstart_mode
    cfg.collider_basis = collider_basis
    solver = SolverImplicitMPM(model, cfg, verbose=solver_diagnostics)
    if rebuildable_sparse and not solver._sparse_rebuildable:
        raise RuntimeError("requested rebuildable sparse path was not activated")
    state, output = model.state(), model.state()
    solver.setup_collider(body_mass=wp.zeros_like(model.body_mass), body_q=state.body_q)
    preparation = []
    preparation_steps = ticks_per_update(settle_dt, settle_s) if settle_s else 0
    for prep_tick in range(preparation_steps):
        captured = io.StringIO()
        with redirect_stdout(captured):
            solver.step(state, output, None, None, settle_dt)
        state, output = output, state
        if solver._sparse_rebuildable:
            solver.check_sparse_grid_rebuild_status()
        diagnostic = captured.getvalue()
        if solver_diagnostics:
            match = re.search(r"terminated after (\d+) iterations with residuals ([^,\s]+), "
                              r"([^\s]+)", diagnostic)
            if match is None or not all(isfinite(float(v)) and float(v) <= tolerance
                                        for v in match.groups()[1:]):
                raise RuntimeError(f"preparation residual failure at step {prep_tick + 1}: "
                                   f"{diagnostic}")
        speeds = np.linalg.norm(state.particle_qd.numpy(), axis=1)
        if not np.isfinite(speeds).all() or not np.isfinite(state.particle_q.numpy()).all():
            raise RuntimeError(f"nonfinite preparation state at step {prep_tick + 1}")
        preparation.append({"time_s": (prep_tick + 1) * settle_dt,
                            "max_particle_speed_m_s": float(speeds.max()),
                            "rms_particle_speed_m_s": float(np.sqrt(np.mean(speeds**2))),
                            "solver_diagnostic": diagnostic})
        if progress is not None and (prep_tick + 1) % 100 == 0:
            print({"phase": "preparation", "completed_steps": prep_tick + 1,
                   "total_steps": preparation_steps}, flush=True)
    preparation_fingerprints = {}
    if preparation_steps:
        arrays = {"particle_q": state.particle_q, "particle_qd": state.particle_qd,
                  "body_q": state.body_q, "body_qd": state.body_qd}
        for name in ("particle_elastic_strain", "particle_transform", "particle_qd_grad",
                     "particle_stress", "particle_Jp"):
            arrays[f"mpm.{name}"] = getattr(state.mpm, name)
        for name, array in arrays.items():
            values = array.numpy()
            if not np.isfinite(values).all():
                raise RuntimeError(f"nonfinite prepared state: {name}")
            preparation_fingerprints[name] = {
                "shape": list(values.shape), "dtype": str(values.dtype),
                "sha256": hashlib.sha256(values.tobytes(order="C")).hexdigest(),
            }
    momentum_metadata = None
    if momentum_audit:
        masses = model.particle_mass.numpy().astype(np.float64)
        gravity = model.gravity.numpy().reshape(-1, 3)
        if len(gravity) != 1:
            raise ValueError("momentum audit requires the single-world fixture")
        previous_momentum = (masses[:, None] * state.particle_qd.numpy()).sum(axis=0)
        gravity_impulse = masses.sum() * gravity[0].astype(np.float64) * dt
        momentum_metadata = {
            "particle_mass_kg": float(masses.sum()),
            "gravity_m_s2": gravity[0].tolist(),
            "initial_particle_momentum_kg_m_s": previous_momentum.tolist(),
            "reaction_sign": "reported collider impulse acts on colliders, opposite to particles",
            "residual_definition": (
                "particle momentum change - gravity impulse + all collider reaction impulses"),
            "qualification": (
                "diagnostic only; background drag and transfer effects are not separately measured"
            ),
        }
    trace = []
    for tick in range(steps):
        time = tick * dt
        z = 0.35 - 0.3 * min(time, 0.8) + 0.3 * max(time - 0.8, 0) + oz
        velocity = -0.3 if time < 0.8 else 0.3
        state.body_q.assign(np.array([[ox, oy, z, 0, 0, 0, 1]], dtype=np.float32))
        state.body_qd.assign(np.array([[0, 0, velocity, 0, 0, 0]], dtype=np.float32))
        diagnostic = ""
        if solver_diagnostics:
            captured = io.StringIO()
            with redirect_stdout(captured):
                solver.step(state, output, None, None, dt)
            diagnostic = captured.getvalue()
            if "residual" not in diagnostic:
                raise RuntimeError("requested solver residual diagnostics were not emitted")
        else:
            solver.step(state, output, None, None, dt)
        state, output = output, state
        if solver._sparse_rebuildable:
            solver.check_sparse_grid_rebuild_status()
        impulses, _, ids = solver.collect_collider_impulses(state)
        indices = ids.numpy()
        mapping = solver.collider_body_index.numpy()
        valid = (indices >= 0) & (indices < len(mapping))
        selected = np.zeros(len(indices), dtype=bool)
        selected[valid] = mapping[indices[valid]] == body
        all_impulses = impulses.numpy()
        impulse = all_impulses[selected].sum(axis=0, dtype=np.float64)
        momentum_row = {}
        if momentum_audit:
            momentum = (masses[:, None] * state.particle_qd.numpy()).sum(axis=0)
            reaction = all_impulses.sum(axis=0, dtype=np.float64)
            change = momentum - previous_momentum
            residual = change - gravity_impulse + reaction
            if not all(np.isfinite(v).all() for v in (momentum, reaction, residual)):
                raise RuntimeError(f"nonfinite momentum accounting at tick {tick + 1}")
            momentum_row = {
                "particle_momentum_kg_m_s": momentum.tolist(),
                "particle_momentum_change_n_s": change.tolist(),
                "gravity_impulse_n_s": gravity_impulse.tolist(),
                "all_collider_reaction_n_s": reaction.tolist(),
                "unassigned_collider_reaction_n_s": (
                    all_impulses[~valid].sum(axis=0, dtype=np.float64).tolist()),
                "unaccounted_momentum_n_s": residual.tolist(),
            }
            previous_momentum = momentum
        particles = state.particle_q.numpy()
        if not np.isfinite(impulse).all() or not np.isfinite(particles).all():
            raise RuntimeError(f"nonfinite state at tick {tick + 1}")
        trace.append(
            {
                "time_s": (tick + 1) * dt,
                "input_z_m": z,
                "input_vz_m_s": velocity,
                "impulse_n_s": impulse.tolist(),
                "solver_diagnostic": diagnostic,
                **momentum_row,
            }
        )
        if progress is not None:
            progress(tick + 1, steps)
    force = windowed_force([row["impulse_n_s"][2] for row in trace], dt, 0.02)
    residuals = []
    if solver_diagnostics:
        for row in trace:
            match = re.search(r"terminated after (\d+) iterations with residuals ([^,\s]+), "
                              r"([^\s]+)", row["solver_diagnostic"])
            if match is None:
                raise RuntimeError("unsupported solver residual diagnostic format")
            count, l2, linf = int(match[1]), float(match[2]), float(match[3])
            residuals.append({"finite": isfinite(l2) and isfinite(linf),
                              "within_tolerance": isfinite(l2) and isfinite(linf)
                              and l2 <= tolerance and linf <= tolerance,
                              "at_iteration_limit": count >= iterations})
    return {
        "dt_s": dt,
        "duration_s": steps * dt,
        "world_offset_m": list(world_offset),
        "momentum_accounting": momentum_metadata,
        "preparation": {"duration_s": settle_s, "dt_s": settle_dt,
                        "trajectory": preparation,
                        "state_fingerprints": preparation_fingerprints,
                        "fingerprint_scope": (
                            "Listed particle and body arrays; not a solver checkpoint"),
                        "claim": "Fixed-duration preparation; equilibrium is not asserted"},
        "boundary": "kinematic prescribed box, zero rotation; no actuator or proxy feedback",
        "mpm": {
            "iterations": iterations,
            "tolerance": tolerance,
            "solver_diagnostics": solver_diagnostics,
            "voxel_m": voxel,
            "spacing_m": spacing,
            "grid_margin_m": 0.0 if rebuildable_sparse else 0.4,
            "grid_padding_cells": cfg.grid_padding,
            "particle_count": model.particle_count,
            "air_drag": air_drag,
            "friction": 0.6,
            "young_modulus_pa": young_modulus,
            "poisson_ratio": 0.3,
            "integration_scheme": integration_scheme,
            "collider_basis": solver.collider_basis,
            "velocity_basis": solver.velocity_basis,
            "grid_type": grid_type,
            "max_active_cells": max_active_cells,
            "resolved_sparse_rebuildable": solver._sparse_rebuildable,
            "requested_warmstart": warmstart_mode,
            "resolved_stress_warmstart": solver._stress_warmstart or "none",
            "sparse_capacity_checked_each_step": solver._sparse_rebuildable,
        },
        "peak_20ms_mean_n": max(force),
        "total_vertical_impulse_n_s": sum(row["impulse_n_s"][2] for row in trace),
        "min_particle_z_m": float(particles[:, 2].min()),
        "final_particle_positions_m": particles.tolist(),
        "trajectory": trace,
        "claim": "Numerical isolation diagnostic, not physical validation",
        "solver_health": None if not solver_diagnostics else {
            "steps": len(residuals),
            "nonfinite_residual_steps": sum(not r["finite"] for r in residuals),
            "outside_tolerance_steps": sum(not r["within_tolerance"] for r in residuals),
            "at_iteration_limit_steps": sum(r["at_iteration_limit"] for r in residuals),
            "passed": all(r["within_tolerance"] for r in residuals),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dt", type=float, nargs="+", default=[0.005, 0.0025, 0.00125])
    parser.add_argument("--voxel", type=float, default=0.04)
    parser.add_argument("--spacing", type=float, default=0.02)
    parser.add_argument("--air-drag", type=float, default=1.0)
    parser.add_argument("--young-modulus", type=float, default=1e15)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--solver-diagnostics", action="store_true")
    parser.add_argument("--integration-scheme", choices=("pic", "gimp"), default="pic")
    parser.add_argument("--collider-basis", choices=("S2", "Q1", "pic"), default="S2",
                        help="Contact sampling basis; production defaults are unchanged")
    parser.add_argument("--momentum-audit", action="store_true",
                        help="Record particle momentum, gravity and all collider reactions")
    parser.add_argument("--settle-s", type=float, default=0.0)
    parser.add_argument("--settle-dt", type=float, default=0.0025,
                        help="Preparation timestep, independent of digging timestep")
    parser.add_argument("--grid-type", choices=("fixed", "sparse"), default="fixed")
    parser.add_argument("--max-active-cells", type=int, default=1 << 18)
    parser.add_argument("--rebuildable-sparse", action="store_true")
    parser.add_argument("--warmstart-mode", choices=("auto", "none", "particles", "grid"),
                        default="auto")
    parser.add_argument("--world-offset", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--progress-every", type=int, default=0,
                        help="Print progress every N physics steps; zero disables progress")
    parser.add_argument("--zero-initial-stress-delta", action="store_true",
                        help="Diagnostic only: zero borrowed Newton stress-delta scratch storage")
    args = parser.parse_args()
    if len(set(args.dt)) != len(args.dt):
        parser.error("timesteps must be distinct")
    if args.max_active_cells <= 0:
        parser.error("active-cell capacity must be positive")
    if args.rebuildable_sparse and args.grid_type != "sparse":
        parser.error("--rebuildable-sparse requires --grid-type sparse")
    if args.rebuildable_sparse and args.warmstart_mode == "grid":
        parser.error("rebuildable sparse does not support grid warm starts")
    if not all(isfinite(v) for v in args.world_offset):
        parser.error("world offset must be finite")
    if args.progress_every < 0:
        parser.error("progress interval must be nonnegative")
    if not isfinite(args.settle_s) or args.settle_s < 0:
        parser.error("settling duration must be finite and nonnegative")
    if not isfinite(args.settle_dt) or args.settle_dt <= 0:
        parser.error("settling timestep must be finite and positive")
    if args.settle_s:
        ticks_per_update(args.settle_dt, args.settle_s)
    if not all(isfinite(v) and v > 0 for v in (args.voxel, args.spacing)):
        parser.error("spatial sizes must be finite and positive")
    if not isfinite(args.air_drag) or args.air_drag < 0:
        parser.error("air drag must be finite and nonnegative")
    if not isfinite(args.young_modulus) or args.young_modulus <= 0:
        parser.error("Young's modulus must be finite and positive")
    if args.iterations <= 0 or not isfinite(args.tolerance) or args.tolerance <= 0:
        parser.error("solver iterations and tolerance must be positive and finite")
    for extent in (0.4, 0.4, 0.2):
        ticks_per_update(args.spacing, extent)
    for dt in args.dt:
        ticks_per_update(dt, 1.2)
        ticks_per_update(dt, 0.02)
    args.output.mkdir(parents=True, exist_ok=False)
    identity = source_identity(Path.cwd())
    wp.config.kernel_cache_dir = str(Path(".cache/warp").resolve())
    wp.init()
    if args.zero_initial_stress_delta:
        # Controlled diagnostic on the pinned dependency; never changes the installed source.
        # Active constraints overwrite this scratch array. Inactive entries should contribute zero.
        from newton._src.solvers.implicit_mpm.solve_rheology import _RheologySolver

        original_init = _RheologySolver.__init__

        def initialized_scratch(self, *init_args, **init_kwargs):
            original_init(self, *init_args, **init_kwargs)
            self.delta_stress.zero_()

        _RheologySolver.__init__ = initialized_scratch
    results = []
    with wp.ScopedDevice("cuda:0"):
        for dt in args.dt:
            started = perf_counter()

            def progress(tick, steps, case_dt=dt, case_started=started):
                if args.progress_every and (tick % args.progress_every == 0 or tick == steps):
                    print({"dt_s": case_dt, "completed_steps": tick, "total_steps": steps,
                           "wall_time_s": perf_counter() - case_started, "terminal": False},
                          flush=True)

            try:
                record = run(dt, args.voxel, args.spacing, args.air_drag, args.young_modulus,
                             args.iterations, args.tolerance, args.solver_diagnostics,
                             args.integration_scheme, args.grid_type, args.max_active_cells,
                             args.rebuildable_sparse, args.warmstart_mode, args.world_offset,
                             progress if args.progress_every else None, args.collider_basis,
                             args.momentum_audit, args.settle_s, args.settle_dt)
            except Exception as error:
                (args.output / "failure.json").write_text(
                    json.dumps(
                        {
                            "dt_s": dt,
                            "source": identity,
                            "error": f"{type(error).__name__}: {error}",
                            "completed_cases": results,
                        },
                        indent=2,
                    )
                )
                raise
            record.update(source=identity, environment=environment_info())
            record["zero_initial_stress_delta"] = args.zero_initial_stress_delta
            record["source_changed"] = (
                identity["source_sha256"] != source_identity(Path.cwd())["source_sha256"]
            )
            record["wall_time_s"] = perf_counter() - started
            (args.output / f"dt-{dt}.json").write_text(json.dumps(record, indent=2))
            results.append(
                {
                    k: record[k]
                    for k in (
                        "dt_s",
                        "peak_20ms_mean_n",
                        "total_vertical_impulse_n_s",
                        "source_changed",
                        "solver_health",
                    )
                }
            )
            (args.output / "summary.json").write_text(json.dumps(results, indent=2))
            print(results[-1], flush=True)
    return int(any(row["source_changed"] or (row["solver_health"] is not None
                   and not row["solver_health"]["passed"]) for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
