# Contact sampling basis control

The 20 mm grid, 10 mm particle spacing, 1.25 ms timestep prescribed-box case
was repeated with Newton's `Q1` contact basis instead of its default `S2`.
The velocity basis remains `Q1`. Material, trajectory, alignment, allocation
capacity, warm start and inner tolerance match the completed timestep case.

| Contact basis | Impulse (N s) | Peak 20 ms mean (N) | Inner checks |
|---|---:|---:|---|
| S2 (default) | 64.686138 | 671.249155 | 960/960 pass |
| Q1 | 51.285176 | 490.786863 | 960/960 pass |

The substantial difference demonstrates sensitivity to contact discretization.
It does not establish which basis is physically accurate or qualify a production
change. The Q1 process exited successfully; all raw residual checks passed and
source files were unchanged during execution. Its recorded run time was 67.5 s.

The isolated source under `runs/numerical-contact-basis` copies the previous
`numerical-grid-alignment` snapshot, adding only the explicit contact-basis
selector and resolved basis metadata to the diagnostic, with the existing kernel
cache path. Source identity is retained in the raw record; it differs from the
earlier snapshot and is not represented as an identical-source rerun.

Compressed raw evidence, its canonical checksum and an independent raw-record
audit are in `evidence/contact-basis/`. The audit uses the shared
`contact-spatial-refinement/reproduce.py` implementation. No physical measurements
were fitted. The next control is timestep refinement with this basis, followed by
spatial refinement if temporal error can be bounded; a lower force is not itself
an improvement in accuracy.
