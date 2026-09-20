# Genesis comparison feasibility

Source review only. No Genesis installation, runtime comparison, backend
replacement or physical qualification is claimed.

The reviewed v1.4.0 tag resolves to commit
`0ce793b42c945b6848aad624501b2ca756d3e244`. Four downloaded source files match
their listed Git blob hashes; SHA-256 checksums are retained in
`evidence/genesis-feasibility/source-review.json`.

The [legacy coupler](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/couplers/legacy_coupler.py)
computes rigid reaction from material momentum change divided by substep time.
The [accumulator](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/solvers/rigid/abd/misc.py)
stores its negative in `cfrc_coupling_vel`, separately from applied forces.
The [forward dynamics code](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/solvers/rigid/abd/forward_dynamics.py)
consumes and clears that coupling wrench. This identifies a candidate measurement
path, not a verified sensor: full simulator scheduling, substep accumulation,
sign, and response for a prescribed body still require checks.

Before a comparison, pin an isolated dependency environment and reproduce the
same geometry, motion and reported observables. Explicitly account for different
constitutive laws and numerical methods. Verify zero-contact readings and
equal-and-opposite momentum exchange before interpreting soil force. Repeat
time and spatial refinement in that backend; agreement with Newton alone cannot
establish physical accuracy. The physical-data admission requirements remain.
