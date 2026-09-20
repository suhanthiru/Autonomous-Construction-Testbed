# Timestep control with matching prepared-state arrays

Each case prepares the same Q1 fixture for one second using 2.5 ms preparation
steps. Only the subsequent digging timestep changes. The isolated source is
`runs/numerical-preparation-fingerprints`, digest
`86044e2ac005d0e95ec1f1af0967d8daa193432b109d9e07dfc0332d332047e5`.

| Digging timestep | Impulse (N s) | Peak 20 ms mean (N) | Digging inner checks |
|---|---:|---:|---|
| 2.5 ms | 47.475946 | 449.353000 | 480/480 pass |
| 1.25 ms | 49.764586 | 466.955540 | 960/960 pass |
| 0.625 ms | Pending | Pending | Running |

Both completed cases pass all 400 preparation residual checks. Their nine recorded
prepared-state arrays have identical shape, dtype and SHA-256 fingerprints:
positions, velocities, body poses/velocities, elastic strain, particle transform,
velocity gradient, stress and plastic volume ratio. This is equality of the listed
arrays, not a complete internal solver checkpoint or an equilibrium certificate.

The first timestep halving increases impulse by 4.82%. Matching recorded prepared
states therefore does not remove temporal sensitivity. No timestep convergence,
spatial convergence or physical validation is claimed. The middle case also
reproduces the previous one-second-preparation result's tool impulse exactly.

Raw cases, per-case audits and checksums are retained in
`evidence/contact-prepared-time/`. The full comparison checker requires all three
cases and rejects differing starting-array fingerprints, configuration or source.
It remains incomplete until the final case is retained and audited.
