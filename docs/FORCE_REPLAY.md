# Exploratory laboratory penetration replay

The square-rod fixture follows the published laboratory scale: 12.7 mm square rod,
216 mm diameter chamber, 267 mm initial bed height, 10 mm/s penetration, quartz
grain density 2,500 kg/m3, and packing fraction 0.57. A 32-plane polygon approximates
the cylindrical chamber. Initial particles are uniformly placed with the specified
bulk density; fluidization, compaction history, and initial settling are not reproduced.

The [data admission audit](DATA_ADMISSION.md) explains the force inference and depth
transformation. Comparison uses the published shifted depth coordinate and force
sign, without fitting offsets. The comparison interval is 0 to 70 mm. These are
development comparisons, not independent physical validation.

```sh
python scripts/replay_rheometer.py --output runs/rheometer-development
python scripts/replay_rheometer.py --voxel .006 --spacing .003 --output runs/rheometer-refinement
```

Both runs use 10 ms steps, friction 0.6, tool friction 0.5, and numerical air drag 1.0.
The rod follows prescribed motion. Its reaction force comes from MPM collider impulse
divided by timestep, not from the dynamic actuator fixture. Reports record settings,
input checksum, source fingerprints, environment, and the full simulated force trace.

| Grid / particle spacing | Particles | Force MAE | Force RMSE | Final force |
|---|---:|---:|---:|---:|
| 9 / 4.5 mm | 108,240 | 3.262 N | 3.515 N | 1.805 N |
| 6 / 3 mm | 361,340 | 3.136 N | 3.363 N | 1.800 N |

The transformed published curve gives approximately 6.98 N at 70 mm. The predicted
resistance is substantially lower. Finer discretization alone does not explain this
mismatch. No friction fit was attempted, and no physical pass threshold was invented.

The two predicted traces differ by 0.269 N mean absolute force and 1.013 N maximum.
Two spatial resolutions with a fixed timestep do not establish convergence. Even
the finer grid has only about two cells across the rod. Preparation, constitutive
response, boundary approximation, initial equilibrium, temporal resolution, and
measurement uncertainty remain unresolved sources of discrepancy.

[Evidence](evidence/force-replay/summary.json) preserves both reports. Their full source
hashes match and neither recorded a source change during execution. Later script
changes add invalid-input checks and failure metadata without changing the successful
simulation path. The source dataset has no explicit repository license; raw measured
curves remain local and are not redistributed here.
