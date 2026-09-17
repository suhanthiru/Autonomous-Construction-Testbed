# Body, soil, and ground momentum ledger

The fixture now records particle momentum, MPM impulse on the static ground, soil
mass, and mass below a 4 cm ground tolerance. Particle momentum and collider impulse
sums use float64 accumulation of the engine's float32 values. The fixture has one
dynamic tool and one static ground plane; the ground channel is not a general
classifier for arbitrary static obstacles.

## Signs and accounting

MPM collider impulses are forces on the collider integrated over the step. Their
opposites act on the soil. With positive vertical direction upward:

- Soil residual: `ΔP_soil + M_soil*g*dt + J_tool + J_ground`.
- System residual: `Δ(P_body + P_soil) - (F_actuator - M_total*g)*dt + J_ground`.
- Feedback difference: `J_actually_applied_to_body - J_generated_by_MPM`.

The report shows the raw system residual and the residual after subtracting the
feedback difference. The latter attributes error; it does **not** repair physical
momentum or turn a delayed interaction into a conservation pass. Residuals can also
include other unrecorded forces, solver errors, or numerical losses.

```sh
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --steps 240 --output runs/system-driven.json
python scripts/check_soil_coupling.py --hold --control-dt 0.005 --steps 240 --output runs/system-hold.json
python scripts/audit_system_momentum.py runs/system-driven.json runs/system-hold.json
```

`--hold` commands zero velocity while gravity compensation holds the tool above
the bed. It retains force limits and dynamic integration. It is a control for soil
settling without tool contact, not a kinematically fixed boundary.

## Scope limits

This ledger covers vertical linear momentum only. It does not assess angular
momentum, mechanical energy, realistic soil resistance, or long-run excavation.
Recorded soil mass is the sum of the fixed particle masses; it does not establish
that particles remain inside the solver's active domain. The ground-tolerance
counter specifically measures particles below z = -0.04 m and is not a general
escaped-mass metric. The fixture remains experimental.

## Measured results

Both 1.2-second runs used the RTX 4060 laptop, a 5 ms physics/controller period,
and one coupling iteration. The [full per-step ledger](evidence/system-momentum/audit.json)
includes canonical record hashes; full input records are stored alongside it.

| Metric | Driven tool | Stationary control |
|---|---:|---:|
| Largest soil momentum residual (N s) | 0.00014438 | 0.00014438 |
| Total signed soil residual (N s) | 0.00655898 | 0.00655095 |
| Largest raw system residual (N s) | 0.25227890 | 0.00014438 |
| Largest residual after accounting for feedback difference (N s) | 0.00014443 | 0.00014438 |
| Maximum mass below ground tolerance (kg) | 0 | 0 |

The stationary run reports zero tool-contact impulse and a final tool height of
0.349999994 m, matching its 0.35 m starting height to float32 precision. The remaining
soil residual is also present without excavation contact. This points to the
soil/ground solve or its momentum measurement as the next place to investigate;
it does not yet identify an engine defect or establish an acceptable tolerance.

The much larger transient system mismatch in the driven case is accounted for by
the difference between generated and applied coupling impulses. Subtracting that
difference is diagnostic only; the recorded raw system mismatch remains visible.

Each record identifies its exact source hashes and reports no source modification
during execution. The driven record preceded addition of the stationary-control
option, so the two source hashes differ. Their numerical solver settings are the
same; the added control commands zero velocity instead of the penetration trajectory.

No conservation or physical-validation pass is claimed. Next checks should isolate
the soil/ground baseline's timestep, spatial resolution, and solver tolerance before
interpreting the smaller residual as acceptable numerical error.
