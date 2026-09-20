# Timestep refinement at a fixed 20 mm grid

This study holds the physical prescribed-box fixture, 20 mm grid and 10 mm
particle spacing fixed, reducing timestep from 2.5 ms to 1.25 and 0.625 ms.
It separates temporal sensitivity from the earlier joint grid/time refinement.

| Timestep | Impulse (N s) | Peak 20 ms mean (N) | Inner residual checks |
|---|---:|---:|---|
| 2.5 ms baseline | 60.256227 | 622.414253 | 480/480 pass |
| 1.25 ms | 64.686138 | 671.249155 | 960/960 pass |
| 0.625 ms | Pending | Pending | Running |

The first halving increases impulse by 7.35% and peak by 7.85%. This does not
establish timestep convergence. Neither case is physical validation.

Both completed records use source digest
`9298bc41be4feecd12b5bbb94d797aa3e522c850f8dfa4fea6e4a76ff45c891e`,
unchanged during execution, and residual tolerance 1e-5. Raw trajectories and
solver logs are retained as compressed JSON with canonical-content checksums.
The 1.25 ms case completed in 467 seconds; no throughput qualification is inferred.

Allocation capacity increases from 65,536 to 262,144 cells, with sparse capacity
checked every step. The warm-start request changes from auto to particles; both
resolve to particles. These bookkeeping differences are recorded explicitly;
the configurations are not identical except for timestep. Geometry, material,
alignment and resolved integration settings are retained.

The checker in `evidence/contact-time-20mm/reproduce.py` uses checksum-verified raw
configuration fields, recomputes force metrics and residual health, and rejects
missing cases. It will refuse a complete study audit until the final record is
available. The completed first case has separately passed that raw-record audit.
