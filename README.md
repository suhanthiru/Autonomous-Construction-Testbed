# Autonomous Construction Testbed

A modular research testbed for excavation and interaction with changing terrain.
Experiments use a versioned simulator, declared observations and actions, and independent
evaluation. Physics claims are tied to measured evidence and a stated operating range.

Start with the [install-to-report guide](docs/REPRODUCE.md). The complete reference
workflow is `python scripts/run_release_workflow.py --output runs/reference-workflow`.
It generates data, trains the baseline, evaluates frozen scenarios, and writes reports.

For exact delivery boundaries, see [completion status](docs/COMPLETION_STATUS.md).

## Current status

The simulator provides coupled soil and a four-joint machine, external policies and
tasks, masked terrain observations, recording, compressed datasets, baseline training,
frozen-scenario evaluation, live control and offline replay. Repeated excavation has
passed the 0.5 kg deposit task on a frozen run without resetting soil: 0.512 kg in
58.54 simulated seconds. The complete six-stage data/training/evaluation workflow
finished with unchanged source. See the [executed release report](docs/evidence/release-v1/README.md).

Software checks pass 52 tests, lint, package build and clean installation; GitHub CI
passes on Windows and Linux. Physical validation has **not** passed. Numerical force
and terrain sensitivity and shared-tool repeatability remain explicit qualification
limits; see the [validation status](docs/VALIDATION_STATUS.md).

The [force-limited penetration check](docs/ACTUATION_CHECK.md) records actuator and
soil forces; its timestep study exposes unresolved peak-force sensitivity.
The [fixed-controller follow-up](docs/CONTROL_CLOCK_STUDY.md) confirms that separating
controller timing does not resolve the numerical sensitivity.
The [momentum audit](docs/MOMENTUM_AUDIT.md) verifies rigid-body impulse accounting
and distinguishes generated soil impulse from delayed applied feedback.
The [combined body/soil/ground ledger](docs/SYSTEM_MOMENTUM.md) isolates a smaller
soil-side residual that is also present in a stationary-tool control.
The [air-drag isolation](docs/AIR_DRAG_CHECK.md) explains most of that small residual.
[Public-data admission](docs/DATA_ADMISSION.md) and a [terrain replay](docs/TERRAIN_REPLAY.md)
are now implemented. The replay completes with plane boundaries, but numerical
convergence and physical acceptance remain unresolved.
The [validation coverage report](docs/VALIDATION_STATUS.md) lists required gates and
returns a nonzero exit status until the recorded evidence supports completion.
An [exploratory penetration replay](docs/FORCE_REPLAY.md) completes at two spatial
resolutions and substantially underpredicts the published laboratory resistance.

## Development setup

Python 3.12 or newer:

```sh
python -m venv .venv
# Activate the environment using the command for your shell.
python -m pip install -e ".[dev]"
excavation-sim doctor
python -m pytest
python -m ruff check src scripts tests experiments
```

The optional physics dependency is installed with `python -m pip install -e ".[physics]"`.
Hardware support is checked separately from the CPU test suite. A passed CPU suite does
not imply GPU or physical validation.

## Design and validation

- [Project scope](SCOPE.md)
- [Validation and public-data replay plan](docs/VALIDATION_PLAN.md)
- [Simulator API and conventions](docs/API.md)
- [Experiment and comparison protocol](docs/EXPERIMENT_PROTOCOL.md)
- [Geometry and data provenance](docs/ASSET_PROVENANCE.md)

The stable simulator is the main deliverable. Probing, QAM, and cooperative manipulation
are separate experiments. Necessary physics changes receive new versions and rerun the
affected validation; experiments cannot silently alter their testbed.

## Executed development workflows

See [the world adapter](docs/WORLD_ADAPTER.md), [machine implementation](docs/ARTICULATED_MACHINE.md),
and [release ledger](docs/IMPLEMENTATION_PROGRESS.md). For a recorded tool episode:

```sh
python scripts/run_tool_episode.py --actions 100 --inspect --output runs/tool-demo
```

For an experimental machine episode (task success is reported separately):

```sh
python scripts/run_tool_episode.py --machine --policy experiments/excavator_edge_cut.py --policy-class ExcavatorPolicy --world-config configs/machine-development.json --actions 1350 --task deposit --inspect --output runs/machine-demo
```

Open the generated `inspection.html` locally to inspect the episode. It uses no external
web assets. The original single-cut development run deposited 0.4224 kg, below its unchanged
0.5 kg task goal; the repeated-cut example in the install guide passes that goal. A linear behavior-cloning evaluation with delayed, noisy sensors
deposited zero. A completed simulation is not a successful excavation demonstration.

The [shared-soil two-tool fixture](docs/SHARED_TOOLS.md) also executes contact, but its
first repeated-trajectory check diverged. Multiagent reproducibility remains unresolved.
