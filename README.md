# Autonomous Construction Testbed

A modular research testbed for excavation and interaction with changing terrain.
Experiments use a versioned simulator, declared observations and actions, and independent
evaluation. Physics claims are tied to measured evidence and a stated operating range.

## Current status

Early implementation: core contracts, episode recording, runtime diagnostics, and tests.
An isolated GPU rigid-body/soil fixture runs with an empty-bed control; see the
[measured feasibility results](docs/COUPLING_FEASIBILITY.md). Physical validation has not
been performed. The full excavator and learning benchmarks are not implemented yet.
The [force-limited penetration check](docs/ACTUATION_CHECK.md) records actuator and
soil forces; its timestep study exposes unresolved peak-force sensitivity.
The [fixed-controller follow-up](docs/CONTROL_CLOCK_STUDY.md) confirms that separating
controller timing does not resolve the numerical sensitivity.

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
