# End-to-end system report

Frozen workflow completed: **True**.
Repeated deposit task succeeded: **True**.
Validation complete: **False**.

The workflow covers named scenarios, recording, compressed datasets, actual baseline
training, held-out scripted/baseline evaluation and generated reports. The repeated
demonstration carries soil across cuts without resetting the world.

## Results

See `scripted/report.md`, `baseline-test/report.md`, their figures and raw JSON summaries.
Repeated task: 0.5120 kg deposited in 58.54 simulated seconds.

## Qualification limits

Operational simulation workflow and measured outcomes. Failed numerical and physical gates remain failures; no real-machine accuracy or safety claim.

Other verification jobs shared the GPU during parts of execution. Recorded wall times include contention and compilation; they are not an isolated throughput comparison.

Unresolved gates: rigid_momentum, soil_momentum, contact_convergence, terrain_convergence, force_data_admission, terrain_data_admission, physical_force, physical_terrain, repeated_excavation, machine_actuation, shared_tool_repeatability.

This report does not label an unqualified physics model as validated. The numerical
studies, physical-data comparisons, source identities and checksums remain inspectable.
