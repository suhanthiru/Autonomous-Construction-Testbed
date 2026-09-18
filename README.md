# Autonomous Construction Testbed

A modular research testbed for excavation and interaction with changing terrain.
Experiments use a versioned simulator, declared observations and actions, and independent
evaluation. Physics claims are tied to measured evidence and a stated operating range.

## Current status

Implementation in progress: reusable coupled worlds, articulated machine prototype,
external policy execution, typed episode loading, task evaluation, and offline inspection.
An isolated GPU rigid-body/soil fixture runs with an empty-bed control; see the
[measured feasibility results](docs/COUPLING_FEASIBILITY.md). Physical validation has
not passed. The articulated prototype runs, but successful scoop/deposit and completed
learning benchmarks remain open.
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
python -m ruff check .
```

The optional physics dependency is installed with `python -m pip install -e ".[physics]"`.
Hardware support is checked separately from the CPU test suite. A passed CPU suite does
not imply GPU or physical validation.

## Design and validation

- [Project scope](SCOPE.md)
- [Validation and public-data replay plan](docs/VALIDATION_PLAN.md)

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
python scripts/run_tool_episode.py --machine --policy experiments/excavator_scripted.py --policy-class ExcavatorPolicy --world-config configs/machine-development.json --actions 1200 --task deposit --inspect --output runs/machine-demo
```

Open the generated `inspection.html` locally to inspect the episode. It uses no external
web assets. The current scripted excavation attempts have failed to retain/deposit soil;
a completed simulation is not a successful excavation demonstration.
