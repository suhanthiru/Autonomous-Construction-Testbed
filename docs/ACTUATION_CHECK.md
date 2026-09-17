# Force-limited penetration fixture

The fixture now accepts `--drive`. This applies a vertical velocity servo to the
dynamic box, commanding -0.3 m/s until 0.8 s and +0.3 m/s afterwards. The gain is
150 N s/m, with gravity compensation inside a 60 N total actuator-force limit.
By default, force is computed once per outer step. `--control-dt` sets an independent
servo period; force is held until its next update, including across rigid substeps.
The box remains a free rigid body; it is not a constrained excavator linkage.

```sh
python scripts/check_soil_coupling.py --drive --steps 240 --output runs/driven.json
python scripts/check_soil_coupling.py --drive --steps 480 --dt 0.0025 --output runs/driven-fine.json
python scripts/check_soil_coupling.py --drive --steps 240 --without-soil --output runs/driven-empty.json
python scripts/summarize_fixture.py runs/driven.json runs/driven-fine.json runs/driven-empty.json
```

Recorded channels include vertical position/velocity, requested velocity, actuator
force, and MPM collider impulse. The impulse sums only contacts assigned to the
single dynamic body, excluding the static ground. Dividing impulse by the outer
timestep gives an interval-average contact force, not an instantaneous force sensor.
The summary also integrates contact impulse and vertical actuator work.

## Interpretation limits

Measured on the same RTX 4060 laptop as the initial coupling fixture:

| Metric | 5 ms step | 2.5 ms step |
|---|---:|---:|
| Minimum box-center height | 0.17469 m | 0.17982 m |
| Final box-center height | 0.29504 m | 0.29656 m |
| Peak vertical soil force | 50.46 N | 107.16 N |
| Integrated vertical soil impulse | 10.3522 N s | 10.6442 N s |
| Maximum absolute actuator force | 60 N | 60 N |

**Peak-force convergence is not established.** The peak more than doubles when the
step is halved. Integrated soil impulse differs by about 2.8%; that alone is not a
convergence pass. These results prevent treating the current contact-force output
as a validated research measurement.

The [full records and summary](evidence/actuation/summary.json) preserve both soil
runs and the driven empty-bed control. All three share the same source hash and
report no source changes during execution. Their git revision identifies the parent
commit because the fixture changes were tested before committing; per-file source
hashes identify the implementation that actually ran.

The timestep comparison changes the physics step and the servo update period
together. It is a sensitivity check of the complete fixture, not an isolated solver
convergence study. The subsequent [fixed-controller study](CONTROL_CLOCK_STUDY.md)
separates those clocks.

The coupling is lagged. An impulse reported for one interval must not be assumed
to equal the feedback actually applied to the rigid body during that same interval.
The recorded vertical work does not account for torque, rotation, floor reactions,
soil kinetic/potential energy, or dissipated energy. It is not an energy-balance pass.

No real-world force accuracy or physical validation is claimed. The experiment API,
excavator articulation, calibrated sensors, and independent evaluation gates remain
separate implementation work.
