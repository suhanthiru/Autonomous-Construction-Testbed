# Grid resolution with fixed particle spacing and timesteps

Status: the 10 mm grid run is active; no comparison result is available yet.

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
After retaining the completed raw record and its checksum, run:

```powershell
python docs/evidence/contact-grid-only/reproduce.py
```

The audit checks raw checksums, complete trajectories, inner solver residuals,
source identity, recorded runtime, mass, gravity, and prescribed motion relative
to the ground. It allows only grid width to differ in the recorded MPM settings
and explicitly checks the half-cell translations. It keeps preparation and
digging checks separate. Missing result files currently prevent a full audit.

Two grid resolutions cannot establish an asymptotic convergence rate. Even a
small difference would not resolve the separate timestep sensitivity or validate
forces against a physical measurement. No physical acceptance threshold or
production default is changed by this diagnostic.
