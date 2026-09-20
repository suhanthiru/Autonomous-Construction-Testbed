# Grid resolution with fixed particle spacing and timesteps

Status: completed; the finer grid failed one digging residual check.

| Grid width | Tool impulse (N s) | Peak 20 ms mean (N) | Digging checks |
|---|---:|---:|---:|
| 20 mm | 50.571153 | 475.171633 | 960/960 pass |
| 10 mm | 50.333977 | 510.946787 | 959/960 pass |

Impulse changes by -0.469% and averaged peak by +7.529%. At 0.76125 s,
the fine run reports 200,001 iterations and an infinity-norm residual of
3.59204e-5, exceeding the unchanged 1e-5 tolerance. The process exits with code 1.
All 400 preparation steps pass. Final maximum preparation speed is
0.0108886 m/s; the maximum over the last 100 ms is 0.0311576 m/s.
The evidence audit passes integrity checks and reports `all_inner_checks_passed`
as false. These force differences include an unresolved inner solve; they do not
establish grid convergence. Source remained unchanged.

This control follows the completed particle-resolution study. It compares that
study's 20 mm grid, 5 mm particle case against a 10 mm grid with the same 256,000
particles. Digging uses 1.25 ms steps. Both cases first prepare the bed for one
second at 2.5 ms per step. Preparation duration is not an equilibrium criterion.

The fixture uses a prescribed box and uncalibrated material parameters. The
entire fixture, including the ground, is translated by half a grid cell in each
axis: 10 mm for the baseline and 5 mm for the finer grid. This preserves the
existing alignment convention, but changes global coordinates. Preparation can
also produce different particle states. The comparison therefore measures the
effect of this grid setup, including its preparation and alignment convention.

The study specification and audit are in `evidence/contact-grid-only/`.
The completed raw record and canonical checksum are retained there. Run:

```powershell
python docs/evidence/contact-grid-only/reproduce.py
```

The audit checks raw checksums, complete trajectories, inner solver residuals,
source identity, recorded runtime, mass, gravity, and prescribed motion relative
to the ground. It allows only grid width to differ in the recorded MPM settings
and explicitly checks the half-cell translations. It keeps preparation and
digging checks separate. Audit success means that the retained evidence agrees
with its summaries; it does not turn a failed physics process into a pass.

Two grid resolutions cannot establish an asymptotic convergence rate. Even a
small difference would not resolve the separate timestep sensitivity or validate
forces against a physical measurement. No physical acceptance threshold or
production default is changed by this diagnostic.
