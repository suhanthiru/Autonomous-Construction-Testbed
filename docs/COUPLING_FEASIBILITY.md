# Rigid body / soil feasibility fixture

## Status

Executed on 2026-09-17 with an RTX 4060 Laptop GPU (8 GiB), Python 3.12.14,
Newton 1.6.0, Warp 1.17.0, and NVIDIA driver 566.26 on Windows.
This is a software feasibility check. It does not establish physical accuracy,
numerical convergence, force accuracy, or readiness for research comparisons.

## Reproduce

Install the physics extra, then run from the repository root:

```sh
python scripts/check_soil_coupling.py --output runs/soil.json
python scripts/check_soil_coupling.py --without-soil --output runs/empty.json
```

Outputs cannot overwrite existing files. Each contains the trajectory, package
versions, source hashes, git status, and simulation timestep. CUDA kernel compilation
makes the first invocation substantially slower. This script is an isolated fixture;
it does not yet implement the platform's World interface.

## Setup and observed results

A 0.12 x 0.12 x 0.08 m box with mass 2.304 kg starts with its center at 0.35 m.
The soil case contains 4,000 particles representing a 0.4 x 0.4 x 0.2 m bed,
bulk density 1,600 kg/m³, and nominal mass 51.2 kg. Particles occupy cell centers
without jitter. The MPM voxel size is 0.04 m; friction is 0.6. The ground is flat
and the bed has no side walls. These are fixture parameters, not calibrated material values.

Both cases use 100 outer steps of 0.005 s and four rigid substeps per outer step.
The soil case uses one lagged proxy coupling iteration.

| Quantity at 0.5 s | Soil | Empty bed |
|---|---:|---:|
| Box center height | 0.15665 m | 0.04000 m |
| Lowest soil particle center | 0.00228 m | N/A |
| Nonfinite positions or velocities observed | None | None |

The height difference is consistent with soil supporting the body. The empty-bed
box reaches the floor at its expected half-height. These observations establish
a functioning interaction path; they do not prove conservation or realistic resistance.

The initial control exposed an integration pitfall: the proxy wrapper did not advance
the rigid entry when configured without proxies. The corrected empty-bed control
calls XPBD directly with the same four rigid substeps and refreshes contacts each
substep. The soil path refreshes rigid contacts once per outer step. This difference
must be accounted for before precision contact comparisons.

## Remaining gates

- Contact impulse and momentum/work accounting, including coupling lag.
- Force-limited commanded penetration and withdrawal, with sensor/evaluator separation.
- Timestep, voxel size, solver-iteration, and particle-density sensitivity.
- Escaped material accounting, repeated excavation/deposition, and restart behavior.
- Calibrated public-data replay with held-out validation cases.
- Full excavator articulation, task wrappers, and benchmark evaluation.

There is no physical-validation pass associated with this fixture.
