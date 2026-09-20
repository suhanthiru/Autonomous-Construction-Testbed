# Momentum accounting in the prescribed-contact fixture

The established Q1 case (20 mm grid, 10 mm particles, 1.25 ms timestep) was
repeated with optional particle-momentum accounting. The process completed all
960 steps, passed every inner residual check, and exited successfully. Instrumented
tool impulse is 51.28517595345431 N s, exactly matching the retained uninstrumented
case's reported impulse. Production settings were not changed.

Each step records particle momentum, its change, gravity impulse, summed reaction
on all colliders (including ground), and reactions with unassigned collider IDs.
The accounting residual is particle momentum change minus gravity impulse plus
collider reaction. The sign follows Newton's collider-reaction convention.

| Vertical accounting quantity | N s |
|---|---:|
| Cumulative unaccounted momentum | 0.004190465 |
| Sum of absolute step residuals | 0.004193103 |
| Largest absolute step residual | 0.000026062 |
| Absolute reaction with unassigned collider IDs | 0 |

This case provides no evidence of a large omitted reaction in the tool-force
accounting. It does not prove exact conservation, identify the residual's cause,
or establish the balance at other resolutions. Background drag and transfer
effects are not measured separately. The earlier force refinement differences
remain unresolved; agreement in global momentum does not imply an accurate local
contact-force distribution.

Raw records and canonical checksums are in `evidence/contact-momentum/`.
`reproduce.py` verifies the contact residual logs and checksums, recomputes every
momentum increment and gravity term, checks physical configuration against the
uninstrumented baseline, and reports signed and absolute imbalance. Its saved
output is `audit.json`; an evidence-integrity pass is not a physical certificate.

The isolated snapshot is `runs/numerical-momentum`, derived from
`runs/numerical-contact-basis` with the optional instrumentation. Its source digest
is `d940575b501b7a0b6530608abb125fd14c1adb565351644eb84af7a81de4d09d` and remained
unchanged throughout execution. The checkout script has a subsequent line-wrap
formatting change; source identities are not treated as identical.
