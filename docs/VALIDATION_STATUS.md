# Validation status

Run `excavation-sim validation-status` from the repository root. It exits with status
1 until every required gate is passed. The manifest is `validation/coverage.json`.
Passing assessments require a repository-local JSON evidence record with a matching
canonical SHA-256 digest. This command checks recorded assessments and evidence
integrity; it does not rerun experiments or judge scientific sufficiency automatically.

The implemented software contracts pass 52 CPU tests and lint, with a pinned assessment
in `docs/evidence/software-contracts.json`. This is limited to implemented functionality.
Numerical contact and terrain
convergence remain unresolved. Public-data replays are development comparisons;
neither establishes an independent physical pass.

## What is still needed

- Resolve contact-force and surface sensitivity to timestep and spatial resolution.
- Complete the momentum budget, including numerical drag and coupling delay.
- Establish admissible uncertainty for preparation, motion, and force measurements.
- Declare useful force and terrain tolerances before independent evaluation.
- Freeze calibration and execute the reserved terrain trial once those gates permit it.
- Admit independent force trials with known preparation and repeat grouping.
- Assess repeated scoop/deposit and articulated machine actuation.
- Resolve the shared-soil contact trajectory repeatability discrepancy.

The articulated machine deposits 0.512 kg across two cuts in a development run,
passing its 0.5 kg task goal without resetting soil. That result does not establish
repeated-cycle reliability or actuator accuracy. Public final-surface scans and penetration curves
do not supply evidence for those integrated mechanisms. Completing the available
replay runs cannot close those gaps.
