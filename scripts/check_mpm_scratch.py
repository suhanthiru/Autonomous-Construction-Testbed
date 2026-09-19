"""Small diagnostic for inactive stress-update storage in pinned Newton 1.6.0.

Deliberate NaN poisoning is limited to a temporary solver array. No production
backend or installed dependency source is modified.
"""

import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import newton
import numpy as np
import warp as wp
from newton._src.solvers.implicit_mpm.solve_rheology import _RheologySolver
from newton.solvers import SolverImplicitMPM

from excavation_sim.provenance import environment_info, source_identity


def run(mode):
    builder = newton.ModelBuilder()
    SolverImplicitMPM.register_custom_attributes(builder)
    builder.add_ground_plane()
    builder.add_particle_grid(
        pos=wp.vec3(0.01, 0.01, 0.01), rot=wp.quat_identity(), vel=wp.vec3(0),
        dim_x=4, dim_y=4, dim_z=4, cell_x=0.02, cell_y=0.02, cell_z=0.02,
        mass=1600 * 0.02**3, jitter=0, radius_mean=0.01,
        custom_attributes={"mpm:friction": 0.6},
    )
    model = builder.finalize()
    cfg = SolverImplicitMPM.Config()
    cfg.voxel_size = 0.04
    cfg.grid_type = "fixed"
    cfg.grid_padding = 4
    cfg.max_active_cell_count = 1 << 15
    cfg.max_iterations = 100
    cfg.tolerance = 1e-5
    solver = SolverImplicitMPM(model, cfg, verbose=True)
    state, output = model.state(), model.state()
    coverage = []
    original = _RheologySolver.__init__
    original_release = _RheologySolver.release

    def instrument(self, *args, **kwargs):
        original(self, *args, **kwargs)
        blocks = self.rheology.color_blocks.numpy()
        block_count = int(self.rheology.color_offsets.numpy()[-1])
        covered = np.zeros(self.size, dtype=bool)
        for start, end in blocks[:, :block_count].T:
            covered[int(start):int(end)] = True
        coverage.append({"strain_nodes": self.size, "colored_nodes": int(covered.sum()),
                         "uncolored_nodes": int((~covered).sum())})
        if mode == "zero":
            self.delta_stress.zero_()
        elif mode == "poison":
            self.delta_stress.fill_(self.delta_stress.dtype(float("nan")))

    def inspect_release(self):
        delta = self.delta_stress.numpy()
        invalid = ~np.isfinite(delta).all(axis=1)
        active = np.diff(self.rheology.strain_mat.offsets.numpy()) != 0
        coverage[-1].update(nonfinite_delta_nodes=int(invalid.sum()),
                            nonfinite_active_delta_nodes=int((invalid & active).sum()),
                            nonfinite_empty_delta_nodes=int((invalid & ~active).sum()))
        original_release(self)

    _RheologySolver.__init__ = instrument
    _RheologySolver.release = inspect_release
    captured = io.StringIO()
    try:
        with redirect_stdout(captured):
            solver.step(state, output, None, None, 0.005)
    finally:
        _RheologySolver.__init__ = original
        _RheologySolver.release = original_release
    positions, velocities = output.particle_q.numpy(), output.particle_qd.numpy()
    return {"mode": mode, "coverage": coverage, "diagnostic": captured.getvalue(),
            "positions_finite": bool(np.isfinite(positions).all()),
            "velocities_finite": bool(np.isfinite(velocities).all()),
            "positions_m": positions.tolist(), "velocities_m_s": velocities.tolist()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply-workaround", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    identity = source_identity(Path.cwd())
    wp.config.kernel_cache_dir = str(Path(".cache/warp").resolve())
    wp.init()
    with wp.ScopedDevice("cuda:0"):
        cases = [run(mode) for mode in ("untouched", "zero", "poison")]
        correction = None
        if args.apply_workaround:
            from excavation_sim.backends.newton_compat import install_stress_delta_initialization

            correction = install_stress_delta_initialization()
            assert install_stress_delta_initialization() == correction
            cases.append(run("recovered"))
    result = {"cases": cases, "source": identity, "environment": environment_info(),
              "source_changed": identity["source_sha256"] !=
              source_identity(Path.cwd())["source_sha256"],
              "claim": "Diagnostic of residual storage only; not physical qualification"}
    result["workaround"] = correction
    (args.output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for case in cases:
        print(case["mode"], case["coverage"], case["diagnostic"].splitlines()[-1])
    return int(result["source_changed"])


if __name__ == "__main__":
    raise SystemExit(main())
