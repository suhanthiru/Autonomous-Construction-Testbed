# Fixed-controller timestep study

## Question and protocol

Does contact-force sensitivity persist when controller timing stays fixed?

The driven fixture runs for 1.2 seconds, using a 5 ms controller period in every
case. Physics timesteps are 5, 2.5, and 1.25 ms; each retains four rigid substeps.
The controller samples velocity and updates actuator force only on integer-aligned
controller ticks. Invalid clock ratios raise an error instead of rounding silently.
The command reverses at 0.8 seconds in every case. Soil resolution, particle layout,
solver iterations, actuator gain, and force limit remain unchanged.

```sh
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --dt 0.005 --steps 240 --output runs/fixed-5ms.json
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --dt 0.0025 --steps 480 --output runs/fixed-2p5ms.json
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --dt 0.00125 --steps 960 --output runs/fixed-1p25ms.json
python scripts/summarize_fixture.py runs/fixed-5ms.json runs/fixed-2p5ms.json runs/fixed-1p25ms.json
```

## Measurement definition

Raw peak force is still reported. A second metric integrates the vertical soil
impulse within nonoverlapping, time-zero-aligned 20 ms windows and divides by 20 ms.
This gives every run the same measurement duration. It is an explicitly averaged
measurement, not a replacement for the raw peak or a calibrated force sensor.
Incomplete windows are rejected so a terminal impulse cannot be silently discarded.

No acceptance tolerance was established from physical data. This study reports
sensitivity; it cannot certify physical accuracy. Rigid and soil integration steps
still change together, and a single deterministic particle layout does not establish
robustness across seeds or material conditions.

## Results: convergence not established

Executed on 2026-09-17 on the RTX 4060 laptop. All three records share the same
source hash, report no source changes during execution, and contain exactly 240
controller updates. The actuator force limit remained 60 N.

| Metric | 5 ms | 2.5 ms | 1.25 ms |
|---|---:|---:|---:|
| Minimum box-center height (m) | 0.17469 | 0.17993 | 0.18818 |
| Final box-center height (m) | 0.29504 | 0.29699 | 0.30409 |
| Raw peak vertical soil force (N) | 50.46 | 106.37 | 211.93 |
| Peak 20 ms mean soil force (N) | 43.59 | 39.36 | 49.51 |
| Integrated vertical soil impulse (N s) | 10.3522 | 10.6921 | 11.7678 |

The raw peaks occur at 0.485, 0.4825, and 0.48125 seconds, respectively. Multiplying
each peak by its timestep gives approximately 0.2523, 0.2659, and 0.2649 N s.
This is consistent with a brief contact impulse producing a timestep-dependent force
peak. It does not identify the complete mechanism or validate the impact response.

Fixed-window forces and integrated impulse also remain sensitive. In particular,
integrated impulse changes by about 10.1% between the two finest runs, compared with
3.3% between the coarser pair. The minimum-height change also grows. These three
runs do not demonstrate a converged result. A fixed controller rate alone does not
resolve the sensitivity, and averaging cannot be used to claim a pass.

The [summary](evidence/fixed-control/summary.json) links record filenames and contains
canonical JSON hashes. Full traces are stored alongside it. They remain separate from
the earlier study, whose controller timing changed with the physics step.

## Consequence for the platform

Contact-force comparisons remain experimental. Before promoting this fixture into a
research backend, investigate rigid/MPM impulse transfer and coupling lag, separately
vary solver iterations and spatial resolution, and run controlled impact/penetration
cases with momentum accounting. Material calibration cannot substitute for resolving
these numerical sensitivities.
