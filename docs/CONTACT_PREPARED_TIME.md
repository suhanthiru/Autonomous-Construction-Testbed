# Timestep control with matching prepared-state arrays

Each case prepares the same Q1 fixture for one second using 2.5 ms preparation
steps. Only the subsequent digging timestep changes. The isolated source is
`runs/numerical-preparation-fingerprints`, digest
`86044e2ac005d0e95ec1f1af0967d8daa193432b109d9e07dfc0332d332047e5`.

| Digging timestep | Impulse (N s) | Peak 20 ms mean (N) | Digging inner checks |
|---|---:|---:|---|
| 2.5 ms | 47.475946 | 449.353000 | 480/480 pass |
| 1.25 ms | 49.764586 | 466.955540 | 960/960 pass |
| 0.625 ms | 52.781467 | 490.206067 | 1920/1920 pass |

All three cases pass all 400 preparation residual checks. Their nine recorded
prepared-state arrays have identical shape, dtype and SHA-256 fingerprints:
positions, velocities, body poses/velocities, elastic strain, particle transform,
velocity gradient, stress and plastic volume ratio. This is equality of the listed
arrays, not a complete internal solver checkpoint or an equilibrium certificate.

The first timestep halving increases impulse by 4.82% and peak force by 3.92%.
The second increases impulse by 6.06% and peak force by 4.98%. The successive
changes do not decrease. Matching recorded prepared states therefore does not
remove temporal sensitivity. No timestep convergence, asymptotic order,
spatial convergence or physical validation is claimed. The middle case also
reproduces the previous one-second-preparation result's tool impulse exactly.

Raw cases, per-case audits and checksums are retained in
`evidence/contact-prepared-time/`. The full comparison checker requires all three
cases and rejects differing starting-array fingerprints, configuration or source.
The full audit passed and is retained as `comparison.json`. The run completed
with process exit code 0. This verifies the integrity of the evidence and inner
solves, not numerical convergence or physical accuracy. No threshold was relaxed.

This control does not support unsettled initial conditions as a sufficient
explanation for the timestep sensitivity. That numerical defect remains open;
the existing fixed-preparation configuration is not promoted as a production fix.
