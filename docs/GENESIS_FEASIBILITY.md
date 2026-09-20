# Genesis comparison feasibility

Source review only. No Genesis installation, runtime comparison, backend
replacement or physical qualification is claimed.

A Windows/Python 3.12 dependency dry run resolved 81 packages for Genesis 1.4.0.
It used wheels for native dependencies and the source distribution for pinned
`pygltflib==1.16.0`, whose wheel was unavailable. Exact resolved versions and
archive hashes are retained in `evidence/genesis-feasibility/dependency-resolution.json`.
PyTorch was not included in that resolution; its CUDA setup and actual backend
imports remain to be checked in a separate environment. Resolution success is
not installation or runtime success.

The reviewed v1.4.0 tag resolves to commit
`0ce793b42c945b6848aad624501b2ca756d3e244`. Five downloaded source files match
their listed Git blob hashes; SHA-256 checksums are retained in
`evidence/genesis-feasibility/source-review.json`.

The [legacy coupler](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/couplers/legacy_coupler.py)
computes rigid reaction from material momentum change divided by substep time.
The [accumulator](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/solvers/rigid/abd/misc.py)
stores its negative in `cfrc_coupling_vel`, separately from applied forces.
The [forward dynamics code](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/solvers/rigid/abd/forward_dynamics.py)
consumes and clears that coupling wrench. This identifies a candidate measurement
path, not a verified sensor: full simulator scheduling, substep accumulation,
sign, and response for a prescribed body still require runtime checks.

The [simulator schedule](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/simulator.py)
runs rigid pre-coupling dynamics before legacy coupling on each substep.
Together with the force-clear code, this implies that the pending coupling
wrench after a scene step represents its last substep, rather than an accumulated
scene-step impulse. Use one substep per measured step in the first diagnostic,
or instrument explicit accumulation over every substep. Check this inference
against measured momentum before interpreting force. Other couplers have
different scheduling and must not inherit this assumption.

Before a comparison, pin an isolated dependency environment and reproduce the
same geometry, motion and reported observables. Explicitly account for different
constitutive laws and numerical methods. Verify zero-contact readings and
equal-and-opposite momentum exchange before interpreting soil force. Repeat
time and spatial refinement in that backend; agreement with Newton alone cannot
establish physical accuracy. The physical-data admission requirements remain.
