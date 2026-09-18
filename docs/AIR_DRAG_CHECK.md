# Numerical air drag explains the small soil momentum residual

Newton 1.6.0's implicit MPM configuration defaults to `air_drag=1.0`. In
`free_velocity`, grid velocity is divided by `node_particle_mass + air_drag*dt`.
This term removes momentum but was absent from the initial soil/ground ledger.
It is a numerical regularizer, not a calibrated aerodynamic model.

We repeated the 0.4-second stationary-tool test at the default and at `1e-6`:

| Soil ledger residual | Default drag | Low drag |
|---|---:|---:|
| Largest step magnitude (N s) | 1.4438e-4 | 8.3202e-7 |
| Total signed residual (N s) | 0.00582414 | -0.00000541 |

The reduction supports drag as the dominant omitted term in that small residual.
The actual drag impulse is not directly instrumented; the low-drag run is an
isolation experiment, not a retroactive exact conservation proof. The default has
not been silently changed. All new fixture records state their drag setting.

The driven low-drag comparison remains timestep-sensitive: peak force is 50.48 N
at 5 ms and 106.32 N at 2.5 ms, with fixed 5 ms controller timing. This rejects drag
as an explanation sufficient to resolve the larger contact sensitivity.

[Settling ledger](evidence/air-drag/settling-audit.json) and
[driven comparison](evidence/air-drag/driven-summary.json) include input hashes.
All four raw records are stored beside the reports.
