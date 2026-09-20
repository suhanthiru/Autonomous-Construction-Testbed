# Particle resolution at fixed grid and timestep

The prepared Q1 fixture was repeated with 5 mm particle spacing instead of 10 mm.
Grid width remains 20 mm; digging timestep is 1.25 ms; preparation remains one
second at 2.5 ms. Source, material parameters, tool trajectory, grid alignment,
allocation capacity and inner tolerance are unchanged.

| Particle spacing | Count | Tool impulse (N s) | Peak 20 ms mean (N) |
|---|---:|---:|---:|
| 10 mm | 32,000 | 49.764586 | 466.955540 |
| 5 mm | 256,000 | 50.571153 | 475.171633 |

Both cases pass all 400 preparation and 960 digging residual checks. The finer
particle case increases impulse by 1.62% and averaged peak by 1.76%. Its final
maximum preparation speed is 0.00615143 m/s, so equilibrium is not asserted.

The independent audit verifies that particle count and spacing are the only
recorded MPM configuration differences, and that timestep, alignment, source and
preparation settings match. Prepared arrays necessarily differ in size; this is
not an identical-state comparison. Two particle resolutions do not establish
sampling convergence, bound timestep error or validate physical forces.

The physics process exited successfully and source remained unchanged. Raw data,
canonical checksum, study specification and comparison are in
`evidence/contact-particle-resolution/`. Recompute with
`python docs/evidence/contact-particle-resolution/reproduce.py`.
No production configuration or acceptance threshold was changed.
