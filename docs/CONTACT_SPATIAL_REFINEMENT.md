# Joint spatial and temporal contact refinement

This study refines the prescribed-box diagnostic after correcting sparse-grid
alignment. It is numerical evidence, not validation against physical measurements.
The real excavator and worksite qualification remains open.

## Controlled setup

The physical bed, box, material properties and trajectory are unchanged. Grid
width, particle spacing and timestep are halved together. The ratio of particle
spacing to grid width is 0.5; prescribed speed times timestep divided by grid
width is 0.0375. Each sparse case translates the entire fixture, including the
ground, by half a voxel in each axis to preserve relative cell alignment.

All cases use the rebuildable sparse path, particle stress warm starts, initialized
stress-delta storage, and a capacity check after every step. Both reported inner
residuals must meet 1e-5 at every step. Increasing the iteration budget does not
change this tolerance. Capacity is an allocation limit, not a physical parameter.

Runs use the frozen `runs/numerical-grid-alignment` source snapshot. Its base is
`66f28c3`, with diagnostic controls recorded in the snapshot manifest. The measured
source digest is `9298bc41be4feecd12b5bbb94d797aa3e522c850f8dfa4fea6e4a76ff45c891e`.
Git metadata refers to the enclosing checkout; file hashes identify the actual
isolated source. Concurrent implementation changes are excluded from these runs.

## Completed results

| Grid / particles / timestep | Particle count | Iteration cap | Impulse (N s) | Peak 20 ms mean (N) | Inner checks |
|---|---:|---:|---:|---:|---|
| 40 mm / 20 mm / 5 ms | 4,000 | 50,000 | 66.417351 | 803.1284 | 240/240 pass |
| 20 mm / 10 mm / 2.5 ms | 32,000 | 50,000 | 60.256042 | 622.4203 | 479/480 pass; excluded |
| 20 mm / 10 mm / 2.5 ms | 32,000 | 200,000 | 60.256227 | 622.4143 | 480/480 pass |

The 50,000-budget run missed the maximum residual tolerance at 0.7525 s
(1.571208e-5). It is retained, but excluded from the inner-converged series.
The rerun meets the unchanged tolerance throughout, with no iteration-cap hits,
nonfinite residuals, capacity failures or source changes.

From 40 mm to 20 mm, impulse decreases by approximately 9.3% and averaged peak
force by 22.5%, relative to the coarse values. Two resolutions do not establish
an asymptotic convergence trend. A 10 mm / 5 mm / 1.25 ms case is pending;
its progress messages are not completion evidence.

Joint refinement also does not separately establish temporal and spatial error.
An acceptable trend here would still require checking timestep error at a fixed
fine grid, and sensitivity to soil preparation, domain boundaries and grid phase.
The unprepared, prescribed box does not qualify excavation, actuators, sensors,
mass transport or repeated cycles on a real machine.

## Evidence

The coarse case is `evidence/contact-grid-alignment/aligned-50000.json.gz`.
Both 20 mm cases and their summaries are in `evidence/contact-spatial-refinement/`.
Hashes apply to canonical decompressed JSON (sorted keys, compact separators,
finite numbers only). Raw records include per-step solver output and reaction
impulses, final particles, source hashes, environment and resolved settings.
The compressed records were decoded and checked against the original results.

No physical acceptance threshold is introduced or passed by this study.
