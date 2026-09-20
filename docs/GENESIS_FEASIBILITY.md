# Genesis comparison feasibility

Genesis and its resolved dependencies are installed in the isolated
`runs/genesis-evaluation/.venv` environment. The installer exited successfully;
all six reviewed source files in the installed wheel match their pinned-source
SHA-256 hashes (`evidence/genesis-feasibility/installed-source-check.json`).
CUDA PyTorch 2.8.0+cu126 is installed. Genesis and PyTorch import successfully,
CUDA identifies the RTX 4060 Laptop GPU, and `pip check` exits successfully.
Checks and runtime package hashes are retained in
`evidence/genesis-feasibility/runtime-imports.json`. Two CPU force-accounting
controls have completed; no excavation-backend replacement or physical
qualification is claimed.

A Windows/Python 3.12 dependency dry run resolved 81 packages for Genesis 1.4.0.
It used wheels for native dependencies and the source distribution for pinned
`pygltflib==1.16.0`, whose wheel was unavailable. Exact resolved versions and
archive hashes are retained in `evidence/genesis-feasibility/dependency-resolution.json`.
PyTorch was installed separately from its official CUDA 12.6 wheel. The initial
dependency installation used archive
hashes from the resolution with `--require-hashes --no-deps`; the pygltflib build
environment itself was not fully locked. Resolution and installation success
do not establish runtime correctness.

The reviewed v1.4.0 tag resolves to commit
`0ce793b42c945b6848aad624501b2ca756d3e244`. Six downloaded source files match
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

The [MPM solver](https://github.com/Genesis-Embodied-AI/genesis-world/blob/0ce793b42c945b6848aad624501b2ca756d3e244/genesis/engine/solvers/mpm_solver.py)
scales particle volume and stored mass internally by 1,000. Its mass query and
coupling code divide out that scale. A diagnostic using the raw particle-info
mass must divide by `particle_volume_scale` before computing physical momentum.
Record the actual scale, total physical mass, particle count and active mask;
do not compare scaled particle momentum against an unscaled coupling impulse.

## Initial CPU accounting controls

`scripts/check_genesis_contact_accounting.py` runs a 512-particle sand block with
zero gravity and a fixed rigid box, either separated or in its path. One initial
step applies the velocity command and is explicitly excluded from accounting.
The next 400 steps use 0.1 ms each and one substep per step. Material parameters
are uncalibrated. This is a sensor/accounting control, not the excavation fixture.

| Case | x reaction impulse (N s) | x unaccounted momentum (kg m/s) |
|---|---:|---:|
| Separated | 0 | 0.00000495205 |
| Contact | 0.353616309 | 0.00000540512 |

Both processes exit successfully. The independent audit recomputes every
accounting residual and checks identical recorded numerical settings, mass,
initial momentum and script hash. Raw compressed records and checksums are in
`evidence/genesis-contact-accounting/`; run its `reproduce.py` to recompute.
The observations support the chosen sign and mass scaling in this CPU control.
They do not validate material response, boundary independence, GPU behavior,
or convergence. A Quadrants warning disabled template-mapper caching; no
performance claim is made.

## Initial GPU accounting controls

The same two controls also completed 400 steps each on CUDA. The separated case
again reports zero reaction, with x momentum drift of 0.00000108347 kg m/s.
The contact case reports x reaction impulse 0.353554423 N s and unaccounted
x momentum 0.00000195864 kg m/s. Each raw trace passes its independent accounting
audit. Records are retained in `evidence/genesis-contact-accounting-gpu/`.

The strict paired audit **fails**: initial x momentum differs by
-4.95910646e-9 kg m/s between the two runs. Do not describe them as identical
initial states. No threshold was relaxed to turn that comparison into a pass.
Audit individual traces with the existing `reproduce.py`, specifying
`--folder docs/evidence/genesis-contact-accounting-gpu --case free` or
`--case contact`. The default paired mode still rejects this pair.
The runs overlapped an independent Newton GPU job; their durations are not
performance measurements. GPU excavation response and convergence remain open.

## Prescribed collider boundary

`scripts/check_genesis_prescribed_boundary.py` tests an explicit diagnostic
boundary condition: immediately before legacy coupling, it overwrites the
freely integrated tool pose and velocity with the prescribed values. This
deliberately removes actuator dynamics from the fixture. It checks the actual
collider position and the link velocity fields consumed by contact, including
a direction reversal. It does not modify installed dependency source.

The initial 1 ms probe completed, but Genesis warned that this exceeded its
suggested 0.4 ms timestep. Its source and record are retained as a probe. A repeat
at 0.1 ms completed all 400 steps with maximum position error 2.98024e-9 m,
maximum velocity error 1.19210e-8 m/s, zero angular velocity, and zero coupling
force for the separated tool. The independent raw-record audit passes the
declared 1e-7 position and velocity bounds. Evidence and its `reproduce.py` are
in `evidence/genesis-prescribed-boundary/`.

This establishes the separated CPU boundary check only. The same boundary must
still be checked under load, and its reaction must be reconciled with particle
momentum before using it for the excavation refinement study. It supplies no
actuator or physical-material qualification.

The loaded CPU counterpart places a 64-particle, 0.102400 kg block in the
prescribed tool's path. It completes 400 steps at 0.1 ms, including reversal,
with the same maximum pose/velocity errors. The x reaction impulse is
-0.0342266762 N s; x unaccounted momentum is 1.21013e-7 kg m/s. The independent
audit recomputes each force-to-impulse conversion and particle-momentum residual.
Raw evidence, exact run source (archived as text), and audit are in
`evidence/genesis-prescribed-loaded/`. Recompute using the boundary audit with
`--folder docs/evidence/genesis-prescribed-loaded`.

This supports the instrumented boundary's force accounting under this small
CPU load. It is not an excavation test or a comparison of material accuracy.
The larger fixture and its time, grid and particle refinements remain required.

The earlier small boundary records check position and velocity, not orientation.
They must not be described as verifying the full six-degree-of-freedom pose.
The larger digging diagnostic explicitly resets and checks the collider quaternion
at every coupling evaluation, in addition to position and linear/angular velocity.

## Full digging diagnostic

The first GPU run of `scripts/check_genesis_digging.py` completes 3,000 steps
at 0.4 ms with a 40 mm grid and 20 mm particle spacing. It uses the prescribed
120 x 120 x 80 mm box, a 400 x 400 x 200 mm bed, and the 1.2-second downward/upward
trajectory. The bed is unprepared. Material settings are explicit: E = 1 MPa,
Poisson ratio 0.3, bulk density 1,600 kg/m3, and friction angle atan(0.6).
These do not establish constitutive equivalence to the Newton fixture.

The retained trace reports vertical tool impulse 29.6926573 N s and peak 20 ms
mean vertical force 229.836615 N. Cumulative unaccounted vertical momentum is
-0.000154838 N s. The independent audit recomputes momentum balance including
gravity and all collider reactions, checks the commanded boundary, and verifies
that particles remain inside the instrumented domain's safety margin.
It passes record integrity; no physical accuracy or convergence gate is passed.
Evidence, exact source, and the audit are in `evidence/genesis-digging/`.
A 0.2 ms run is the next time-refinement comparison, with other inputs unchanged.

Before a comparison, pin an isolated dependency environment and reproduce the
same geometry, motion and reported observables. Explicitly account for different
constitutive laws and numerical methods. Verify zero-contact readings and
equal-and-opposite momentum exchange before interpreting soil force. Repeat
time and spatial refinement in that backend; agreement with Newton alone cannot
establish physical accuracy. The physical-data admission requirements remain.
