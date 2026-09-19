# Contact isolation and attempted coupling correction

## Adaptive feedback relaxation

The lagged proxy was tested with four coupling passes and Aitken relaxation, starting
at 0.5 and bounded by the solver's 0.1–1.0 defaults. The 5 ms controller period,
geometry, material, grid and inner solver settings match the earlier control.

| Physics step (ms) | Total vertical impulse (N s) | Peak 20 ms mean (N) | Minimum height (m) |
|---|---:|---:|---:|
| 5 | 10.509 | 39.47 | 0.17929 |
| 2.5 | 11.235 | 46.68 | 0.18538 |
| 1.25 | 12.827 | 54.39 | 0.19673 |

This attempted correction does not establish timestep convergence. It was not
promoted to a production default. All three cases completed without source changes;
records and canonical hashes are in `evidence/contact-aitken/`.

```sh
python scripts/check_coupling_refinement.py --iterations 4 --proxy-relaxation 0.5 --relaxation-mode aitken --output runs/contact-aitken
```

## Remove the controller and rigid feedback

The next fixture uses the same 120 × 120 × 80 mm box and 400 × 400 × 200 mm soil bed.
It prescribes the box origin from z=0.35 m downward at 0.3 m/s until 0.8 s and upward
at 0.3 m/s until 1.2 s. Orientation is fixed. Each timestep follows the same trajectory.
There is no rigid-body integration, force-limited actuator, or coupling-feedback loop.

The fixed MPM grid is 40 mm, particles are spaced 20 mm, density is 1600 kg/m³,
soil friction is 0.6 and tool friction is 0.5. The inner solve uses 100 iterations
and 1e-5 tolerance. Initial soil preparation is unchanged and has no separate settling
stage. This is an isolation fixture, not a laboratory replica.

| Physics step (ms) | Total vertical impulse (N s) | Peak 20 ms mean (N) |
|---|---:|---:|
| 5 | 63.615 | 1022.05 |
| 2.5 | 73.028 | 1041.16 |
| 1.25 | 84.832 | 1133.63 |

![Prescribed-motion comparison](evidence/contact-prescribed/comparison.png)

The successive impulse changes are approximately 14.8% and 16.2%. The discrepancy
persists with the motion and orientation prescribed. Therefore a rigid-feedback-only
correction cannot establish numerical qualification for this configuration. This does
not identify a specific upstream software bug or show that every Newton configuration
has this behavior. Spatial discretization, transfer, preparation and contact treatment
remain possible contributors.

The prescribed box penetrates farther than the force-limited box; its absolute forces
must not be compared as equivalent loads. They are not machine safety ratings.
All records include the exact input path and final particle positions, and report
unchanged source. They are in `evidence/contact-prescribed/` with canonical checksums.

```sh
python scripts/check_prescribed_contact.py --output runs/contact-prescribed
```

## Release consequence

### Spatial refinement and background drag controls

Halving the grid to 20 mm and particle spacing to 10 mm produces the following
results. The physical grid margin is held at 0.4 m, rather than holding the number
of padding cells fixed. Particle count increases from 4,000 to 32,000.

| Physics step (ms) | Total vertical impulse (N s) | Peak 20 ms mean (N) |
|---|---:|---:|
| 5 | 50.802 | 470.97 |
| 2.5 | 57.374 | 555.42 |
| 1.25 | 63.921 | 668.94 |

Successive impulse changes are 12.9% and 11.4%. Neither spatial nor temporal
qualification follows from these results. Records and canonical hashes are in
`evidence/contact-prescribed-spatial-fine/`.

A separate control retains the 40 mm grid and reduces numerical air drag from 1
to 1e-6. Impulses are 63.633, 73.090 and 84.828 N s at the same three timesteps.
Each is within 0.1% of the original corresponding impulse. The background-drag
term does not explain the large timestep sensitivity in this fixture. This result
does not negate its previously observed contribution to the stationary momentum
budget. Records are in `evidence/contact-prescribed-low-drag/`.

```sh
python scripts/check_prescribed_contact.py --voxel 0.02 --spacing 0.01 --output runs/contact-prescribed-spatial-fine
python scripts/check_prescribed_contact.py --air-drag 0.000001 --output runs/contact-prescribed-low-drag
```

All six new cases completed with unchanged source. Existing frozen release records
and production material settings are unchanged.

### Qualification status

#### Inner residual diagnostics

A 1,000-iteration, 1e-7-tolerance control gives impulses of 65.882, 75.275 and
86.114 N s at 5, 2.5 and 1.25 ms. The timestep discrepancy remains. An initial
instrumentation error assigned verbosity to `Config` instead of the solver
constructor, so those records have empty diagnostic strings; their requested
diagnostics flag is not proof of residual convergence. The original files are
preserved in `evidence/contact-prescribed-tight/` with this limitation recorded.
The script now requests verbosity through the constructor and rejects missing logs.

With working instrumentation at the original 100-iteration setting, 169 of 240
steps at 5 ms report nonfinite residuals despite finite forces and particle positions.
The raw logs and assessment are in `evidence/contact-prescribed-residuals/`.

The pinned Newton solver borrows a temporary stress-update array without explicitly
initializing it. A controlled runtime intervention initializes that array to zero
before the solve; installed dependency files and production defaults are unchanged.
This removes the observed nonfinite residuals in three runs, but does not establish
a complete upstream diagnosis or a validated correction.

| Step (ms) | Steps outside 1e-5 inner tolerance | Total steps | Impulse (N s) |
|---|---:|---:|---:|
| 5 | 158 | 240 | 63.616 |
| 2.5 | 229 | 480 | 72.967 |
| 1.25 | 265 | 960 | 84.827 |

The initialized 5 ms control with 1,000 iterations and 1e-7 tolerance still has
201 of 240 steps outside that requested tolerance. Its maximum reported L-infinity
residual is approximately 3.21e-4. No inner-convergence pass is claimed.
Evidence is in `evidence/contact-prescribed-initialized/` and
`evidence/contact-prescribed-initialized-tight/`. Diagnostic runs now return nonzero
when reported residuals are nonfinite or above the requested tolerance.

```sh
python scripts/check_prescribed_contact.py --solver-diagnostics --zero-initial-stress-delta --output runs/contact-prescribed-initialized
```

A finite-compliance control changes only Young's modulus from the upstream
1e15 Pa default to an explicitly uncalibrated 1 MPa. At 5, 2.5 and 1.25 ms it
produces impulses of 54.042, 58.225 and 63.373 N s, respectively. Successive
changes remain 7.7% and 8.8%; this does not establish convergence. These records
are in `evidence/contact-prescribed-compliant/`. The material is a diagnostic
contrast, not a fitted sand model or a production default.

#### Reproduced inactive-entry defect and backend revision 0.2

A smaller fixture has 64 particles and 1,000 strain nodes. Only 8 nodes are
included in the colored solve. Poisoning the temporary stress-update array leaves
992 nonfinite entries, all at empty nodes; active nodes remain finite. The reported
residual becomes nonfinite and the solve runs to its iteration limit. Zeroing the
array restores a finite residual and termination after 46 reported iterations.

`scripts/check_mpm_scratch.py` reproduces this independently of digging or a moving
tool. `newton_compat.py` implements the narrow initialization correction. It checks
both Newton version 1.6.0 and the reviewed constructor's source checksum, installs
once per process, and refuses an unreviewed dependency change. It does not edit
installed dependency files. Because the hook is process-wide, other Newton MPM
solvers subsequently created in that process also receive initialized scratch.

New reusable testbed worlds identify themselves as backend revision **0.2** and
record the correction identifier in their backend metadata. Frozen revision-0.1
results remain unchanged and must not be represented as reruns of revision 0.2.
The earlier private-API diagnostic intervention remains separately identified.

```sh
python scripts/check_mpm_scratch.py --apply-workaround --output runs/mpm-scratch-correction
```

This corrects a demonstrated residual-storage defect. It does not solve the
remaining iteration-limit or timestep-convergence failures, and it provides no
new real-machine physical validation claim.

The operating workflow remains usable for explicitly labeled experiments on its
discrete dynamics. Contact-force prediction and real-world transfer remain unqualified.
No material coefficient, acceptance tolerance, or frozen result was changed to make
these studies pass. Further qualification requires a demonstrably convergent physical
configuration or backend revision, followed by independent measured comparisons.
