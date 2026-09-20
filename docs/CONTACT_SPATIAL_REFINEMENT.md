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
| 10 mm / 5 mm / 1.25 ms | 256,000 | 200,000 | 51.715698 | 422.8910 | 959/960 pass; excluded |
| 10 mm / 5 mm / 1.25 ms | 256,000 | 500,000 | 51.706923 | 422.4283 | 959/960 pass; excluded |

The 50,000-budget run missed the maximum residual tolerance at 0.7525 s
(1.571208e-5). It is retained, but excluded from the inner-converged series.
The rerun meets the unchanged tolerance throughout, with no iteration-cap hits,
nonfinite residuals, capacity failures or source changes.

From 40 mm to 20 mm, impulse decreases by approximately 9.3% and averaged peak
force by 22.5%, relative to the coarse values. Two resolutions do not establish
an asymptotic convergence trend.

The 10 mm / 5 mm / 1.25 ms case completed all 960 steps and returned exit code 1.
At 0.6275 s it reached the 200,000-iteration cap (200,001 reported iterations),
with residuals 1.084016e-7 and 1.821908e-5. The second exceeds 1e-5, so this run
is excluded from the inner-converged series. There were no nonfinite residuals,
source changes or sparse capacity failures. The evidence checker independently
reconstructs the one failed step from the raw diagnostic text.

Its impulse is 14.2% below the 20 mm result and its averaged peak is 32.1% below.
These raw differences do not support a completed convergence claim. Because the
fine run has an unresolved inner error, they also cannot isolate spatial or
temporal error or establish an order of convergence. No extrapolated physical
prediction is reported.

The fine run experienced long execution/observation interruptions. Its recorded
75,975-second elapsed wall time is retained for provenance, but is not a valid
throughput comparison with the uninterrupted coarse runs. The terminal process
result, complete trajectory, unchanged source hashes and residual audit establish
what was executed; no repeatability claim across such interruptions is made.

## Increased fine-grid solver budget

A matched rerun increases only the iteration cap to 500,000. It completes all
960 steps in 1,775.10 seconds and returns exit code 1. The same step at 0.6275 s
still misses tolerance: residuals are 5.267385e-8 and 1.034126e-5 after 500,001
reported iterations. No nonfinite residuals, source changes or sparse capacity
failures are recorded. This run is also excluded from the inner-converged series.

Relative to the 200,000-cap fine run, total impulse changes by approximately
0.017% and averaged peak by 0.109%. This measured budget sensitivity is small
compared with the difference between the 20 mm and 10 mm results. It does not
bound the remaining solver error or turn a failed tolerance check into a pass.
The tolerance remains unchanged. Neither fine run supports an accepted
three-level convergence series, and no physical qualification follows.

## Where the resolution difference occurs

Splitting the existing trajectories at the prescribed 0.8-second motion reversal
localizes the impulse difference to loading. This is an exploratory breakdown of
the same evidence, including the failed fine-grid case, not an acceptance test.

| Grid / iteration cap | Loading impulse (N s) | Withdrawal impulse (N s) | Peak averaging interval (s) |
|---|---:|---:|---|
| 40 mm / 50,000 | 66.434519 | -0.017168 | 0.74–0.76 |
| 20 mm / 200,000 | 60.308483 | -0.052256 | 0.78–0.80 |
| 10 mm / 500,000 | 51.786710 | -0.079787 | 0.78–0.80 |

Withdrawal contributes less than 0.08 N s in magnitude in each case. It cannot
account for the several-newton-second differences in total impulse. The loading
force history and its peak timing therefore need attention; a change confined to
post-reversal behavior would not resolve the observed mismatch. This does not
identify its cause, distinguish spatial from temporal error, or establish which
resolution is physically accurate.

`evidence/contact-spatial-refinement/phase-comparison.json` stores the derived
values for all five records, including failed runs. `reproduce.py` recomputes them
after checking the raw evidence hashes; the loading and withdrawal contributions
were checked to sum to each recorded total. No additional simulation was run for
this breakdown.

Joint refinement also does not separately establish temporal and spatial error.
An acceptable trend here would still require checking timestep error at a fixed
fine grid, and sensitivity to soil preparation, domain boundaries and grid phase.
The unprepared, prescribed box does not qualify excavation, actuators, sensors,
mass transport or repeated cycles on a real machine.

## Evidence

The coarse case is `evidence/contact-grid-alignment/aligned-50000.json.gz`.
Both 20 mm cases, both failed 10 mm cases and their summaries are in
`evidence/contact-spatial-refinement/`.
Hashes apply to canonical decompressed JSON (sorted keys, compact separators,
finite numbers only). Raw records include per-step solver output and reaction
impulses, final particles, source hashes, environment and resolved settings.
The compressed records were decoded and checked against the original results.

To audit the saved evidence without Newton, Warp or a GPU, run:

```powershell
python docs/evidence/contact-spatial-refinement/reproduce.py
```

This standard-library checker verifies canonical hashes, trajectory duration and
timestamps, recomputes impulse and 20 ms mean peaks, and reconstructs solver-health
counts from per-step diagnostics. It reports the retained failed run as failed.
Its successful exit indicates evidence integrity only, not numerical convergence
or physical validation. An invalid checksum is rejected.

No physical acceptance threshold is introduced or passed by this study.
