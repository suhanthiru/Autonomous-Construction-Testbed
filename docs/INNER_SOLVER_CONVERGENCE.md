# Contact comparison after satisfying the inner residual tolerance

This study separates an incomplete inner solve from timestep sensitivity. It does
not qualify physical excavation or the selected real-machine/worksite target.

## Controlled setup

The prescribed box, bed, material and trajectory match `CONTACT_ISOLATION.md`:
120 × 120 × 80 mm box; 400 × 400 × 200 mm bed; 40 mm grid; 20 mm particle
spacing; 1.2 s motion. Stress-update scratch is initialized using the previously
verified correction. Both reported residual tolerances remain **1e-5**. The
iteration cap is increased to **20,000** for all three cases; no tolerance or
material coefficient is relaxed to obtain a pass.

Concurrent source edits invalidated the provenance of an initial 2.5 ms run.
The final comparison instead uses an isolated archive of commit `66f28c3`.
Imports were verified to resolve to that archive's `src` directory. The only local
script adjustment directs kernel caching to the existing cache. All final cases
have the same source checksum and report no source changes during execution.
The contaminated development run remains in `runs/contact-inner-budget-20000/`
and is not used as qualification evidence.

## Results

| Timestep (ms) | Steps meeting both residual tolerances | Maximum reported iterations | Total vertical impulse (N s) | Peak 20 ms mean (N) |
|---|---:|---:|---:|---:|
| 5 | 240 / 240 | 8,431 | 66.207 | 815.07 |
| 2.5 | 480 / 480 | 11,726 | 75.323 | 948.02 |
| 1.25 | 960 / 960 | 5,656 | 86.263 | 1200.38 |

There are no reported nonfinite residuals, steps outside tolerance, or iteration-cap
hits in the final comparison. This establishes the stated **inner residual check
for these three executions**, not general convergence or physical accuracy.
The residual measures the solver's stress update; it does not independently prove
every contact complementarity condition, momentum balance or energy balance.

Successive impulse changes are approximately **13.8% and 14.5%**. Force peaks also
change substantially. Thus timestep sensitivity persists after satisfying the
configured inner residual tolerance. Increasing the production iteration budget
alone would not establish a trustworthy force model. Production defaults were not
changed by this study, and the global contact-convergence gate remains failed.

## Evidence and reproduction

`evidence/contact-inner-converged/summary.json` identifies the snapshot, source
checksums and per-case residual statistics. The compressed records preserve every
step's raw solver diagnostics, impulses, trajectory and final particle positions.
Checksums apply to canonical JSON after decompression.

Run from an isolated checkout of `66f28c3`, with that checkout's package on the
Python import path and the pinned dependencies installed:

```sh
python scripts/check_prescribed_contact.py --iterations 20000 --tolerance 0.00001 --solver-diagnostics --zero-initial-stress-delta --output runs/inner-converged
```

The next numerical investigation must address spatial discretization, particle-grid
transfer and contact treatment while retaining inner residual checks. APIC reduces
transfer diffusion but does not make a transfer step exact for arbitrary velocity
fields; see the [original APIC analysis](https://arxiv.org/abs/1603.06188).
Whether transfer or contact explains this fixture's discrepancy remains a hypothesis
to test, not an established cause. Calibration against measured forces must not hide
this unresolved numerical error.
