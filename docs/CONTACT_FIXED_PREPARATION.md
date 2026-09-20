# Preparation with an independent timestep

The Q1 prescribed-box fixture now supports an optional preparation interval whose
timestep is independent of the digging timestep. Production defaults are unchanged.
The completed control uses a 20 mm grid, 10 mm particles, one second of stationary-
tool preparation at 2.5 ms, followed by the established 1.2-second motion at 1.25 ms.

All 400 preparation and 960 digging solves meet the unchanged 1e-5 residual
tolerance. The process exited successfully with unchanged source. The preparation
audit verifies its complete timestamps and every raw residual separately from the
digging trace.

| Observation | Value |
|---|---:|
| Final maximum preparation speed | 0.00702436 m/s |
| Final RMS preparation speed | 0.000250032 m/s |
| Maximum speed over last 100 ms of preparation | 0.00745641 m/s |
| Digging tool impulse | 49.764586 N s |
| Peak 20 ms mean force | 466.955540 N |

The prepared bed still has residual motion. No equilibrium criterion or physical
acceptance threshold is inferred after seeing these values. Its impulse differs
from the unprepared Q1 case (51.285176 N s), so preparation matters, but this single
case does not establish prepared-bed timestep convergence.

Raw data, canonical checksum and audit output are retained under
`evidence/contact-fixed-preparation/`. Reproduce the audit with
`python docs/evidence/contact-fixed-preparation/reproduce.py`. Source snapshot
`runs/numerical-fixed-preparation` has digest
`6dbc3f98874e080f6a7fc51dee05bc3465867295ef52c515abd3b9156b36b5aa`.

The next control holds the preparation timestep and duration fixed while changing
only the subsequent digging timestep. Prepared states must be checked for
consistency; shared preparation settings alone do not prove identical states.
Neither preparation nor an inner-solver pass replaces spatial convergence or
validation against experimental measurements.
