# Install, run, train, evaluate and inspect

The supported executed GPU profile is Windows 11, Python 3.12, RTX 4060 laptop GPU
with 8 GB VRAM. The 3080 Ti workstation has not been checked. CPU contracts also
have a Linux CI job; that is not a Linux GPU qualification. This is experimental
coupled physics. Read `VALIDATION_STATUS.md` before interpreting measurements.

## Installation

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-build-isolation
.\.venv\Scripts\python.exe -m excavation_sim.cli doctor
.\.venv\Scripts\python.exe scripts/check_software.py --output runs/software-check
```

The lock records the executed development runtime, including physics and plotting.
Newton and Warp use the installed NVIDIA driver; first GPU execution compiles kernels.
All result directories must be new, so previous evidence cannot be silently overwritten.

## Watch and control a machine

```powershell
.\.venv\Scripts\python.exe scripts/serve_sim.py --output runs/live-session
```

Open `http://127.0.0.1:8766/`. Step or play the simulation, select manual joint controls,
reset to a new recorded episode, and use Stop session to preserve and close the run.
The default policy repeats the edge-cut sequence. The terrain layer shows the masked
height sensor; the live status includes deposited mass.
Drag the view to orbit and scroll to zoom. The viewer is a privileged inspection tool;
its particle truth and collision shapes are not policy observations.

For a recorded two-cycle development attempt:

```powershell
.\.venv\Scripts\python.exe scripts/run_tool_episode.py --machine --policy experiments/excavator_edge_cut.py --policy-class ExcavatorPolicy --policy-kwargs configs/policy-repeat.json --actions 3400 --task deposit --inspect --output runs/repeated-demo
```

The simulator stops when the 0.5 kg deposit task succeeds or its budget expires.
The second cycle uses the first cycle's disturbed soil; there is no intermediate reset.
Task failures remain valid completed simulation records, but are never labeled success.

## One command for the full reference workflow

```powershell
.\.venv\Scripts\python.exe scripts/run_release_workflow.py --output runs/reference-workflow
```

This checks hardware, generates a 27-second named training episode, exports compressed
data, fits a ridge behavior-cloning checkpoint, evaluates the scripted and trained
policies on the two frozen test conditions, and writes JSON, Markdown and PNG reports.
The default is 1,350 actions per episode. A short `--actions 5` run checks integration
only and cannot establish excavation performance. Full runs take substantially longer
than simulated time on the laptop. Do not edit source while a frozen workflow runs.

Inspect `workflow.json` for every command, exit code, source identity and measured cost.
`scripted/report.md` and `baseline-test/report.md` contain per-condition outcomes;
`results.json` retains failures, loads, work, escape mass and runtime. Each episode
contains `inspection.html`. Display sampling may be reduced to keep long viewer files
bounded; the full-rate transition and evaluation streams remain intact.

## Separate dataset, training and evaluation commands

```powershell
.\.venv\Scripts\python.exe scripts/run_tool_episode.py --suite scenarios/v1/suite.json --scenario flat-reference --policy experiments/excavator_edge_cut.py --policy-class ExcavatorPolicy --actions 1350 --task deposit --output runs/training-episode
.\.venv\Scripts\python.exe scripts/export_dataset.py runs/training-episode --output runs/training-data
.\.venv\Scripts\python.exe experiments/behavior_cloning.py runs/training-data --suite scenarios/v1/suite.json --output runs/trained-policy
.\.venv\Scripts\python.exe scripts/evaluate_suite.py --policy experiments/behavior_cloning.py --policy-class ClonedPolicy --policy-kwargs runs/trained-policy/policy-kwargs.json --output runs/evaluation
.\.venv\Scripts\python.exe scripts/evaluate_suite.py --policy experiments/behavior_cloning.py --policy-class ClonedPolicy --output runs/evaluation --report-only
```

The shipped `datasets/example-edge-v0` is an older development episode, with original
source provenance. It is useful for offline loader/training checks but is not admitted
to the new frozen suite. Training with `--suite` rejects undeclared and held-out episodes.
Dataset shards are compressed NumPy archives with numeric columns and lossless record
bytes. `excavation_sim.packed.iter_records` verifies checksums, sizes and continuity;
it does not open evaluator diagnostics or enable pickle loading.

## Change experiments without editing physics

Pass an external policy path and class to the runner. Policies implement `reset(seed)`
and `act(observation)`, returning `JointCommand` or `ToolCommand` as appropriate. Terrain
packets and sensor age/validity are documented in `SURFACE_SENSOR.md`. World configuration
and hidden material parameters are not passed to the policy call.

An executed extension example combines three-action chunks and an external contact task:

```powershell
.\.venv\Scripts\python.exe scripts/run_tool_episode.py --policy experiments/chunk_probe.py --policy-class ProbePolicy --task-plugin experiments/contact_task.py --task-class ContactTask --actions 150 --output runs/extension-example
```

`ChunkExecutor` logs proposed chunks and interruptions; transitions record the commands
actually executed. Invalid sensor packets discard pending actions. Removing experiments
does not remove any simulator package module. The shared-soil API is in `SHARED_TOOLS.md`.

## Scenarios and validation

`scenarios/v1/suite.json` declares training, development and test conditions and includes
a canonical checksum. Terrain preparation is deterministic and versioned. A seed change
alone is not treated as a different flat, nonrandom condition. Named test conditions are
not tuning data. A changed suite requires a new version and new reports.

The buried rigid box conditions are original bench-scale approximations, with explicit
dynamic and anchored variants. Soil is removed from their initial volume. Runtime model
metadata records generated masses, inertias, captured transforms with their tick and the audit envelope.
These conditions do not represent fractured rock or validated soil/rock behavior.

```powershell
.\.venv\Scripts\python.exe scripts/check_surface_sensor.py --output runs/surface-check
.\.venv\Scripts\python.exe scripts/check_shared_tools.py --output runs/shared-check
.\.venv\Scripts\python.exe -m excavation_sim.cli validation-status
```

The validation status command deliberately exits nonzero while required gates remain
unresolved. An executed workflow is not proof of physical accuracy. Public-data loaders,
replays, limitations and retained evidence are documented in `DATA_ADMISSION.md`,
`FORCE_REPLAY.md`, `TERRAIN_REPLAY.md` and `VALIDATION_STATUS.md`.

## Executed reference and portable evidence

`docs/evidence/release-v1/README.md` reports the completed full-budget workflow.
Its physics/training execution is frozen at `f9769f3`; subsequent interface metadata,
live-view defaults, data-admission checks and reporting changes have separate evidence.
Do not relabel the frozen results as execution of a later source revision.

The bundle contains 1,350 training transitions, a fitted checkpoint, all held-out
outcomes, compressed full-rate policy/evaluator streams, and the successful repeated
replay at `docs/evidence/release-v1/repeated/inspection.html`. Open that HTML directly.
The replay samples displayed frames; the exact final task state is in `performance.json`.

To use the shipped checkpoint from the repository root, pass
`--policy experiments/behavior_cloning.py --policy-class ClonedPolicy
--policy-kwargs docs/evidence/release-v1/baseline/policy-kwargs.json` to the runner.
Its held-out deposit result was zero on both conditions. This is a functioning trained
reference with measured failures, not a competent excavating learned policy.

The evidence manifest hashes all bundled data. Regenerate a bundle after executing
the workflow and repeated demo using:

```powershell
.\.venv\Scripts\python.exe scripts/assemble_release_report.py --workflow runs/reference-workflow --repeat runs/repeated-demo --output runs/release-report
```

See `EXPERIMENT_PROTOCOL.md` for comparison and claim requirements, `API.md` for
extension contracts, and `ASSET_PROVENANCE.md` for geometry/data origins.
