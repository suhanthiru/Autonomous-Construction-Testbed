# Using the fixed testbed for research

## Freeze before evaluating

Record the repository revision and source fingerprint, dependency lock, scenario-suite
checksum, world/sensor configurations, action budget, task, policy code and checkpoint.
Use an unchanged checkout for the whole comparison. Preserve every attempted episode,
including numerical errors, task failures and interruptions. A physics or observation
change creates a new benchmark version and requires rerunning affected comparisons.

Tune using training and development conditions only. Keep test conditions out of
training and parameter selection. The supplied suite checks scenario admission and
duplicates, but cannot prevent a researcher from manually tuning against test results.
The published two-condition reference evaluation is now public evidence; for a new
confirmatory study, preregister additional unseen conditions before running them.

## Compare an algorithm such as QAM

Implement its policy/trainer outside the simulator. Declare exactly which observations
it consumes, its action representation, chunk length and interruption rules. Match
training data, sensor configuration, interaction budget and evaluation conditions to
the comparator. An oracle using hidden soil properties must be labeled separately.

Use independent training seeds for stochastic algorithms. Evaluate each trained policy
on the same declared condition/seed panel. Report per-run outcomes and a paired
analysis at the independent training-run level; many timesteps from one trajectory
are not independent samples. Determine replication and useful effect sizes before
claiming an improvement. The shipped single linear fit is an integration reference,
not a statistically established algorithm ranking.

Report task success, deposited mass, work, load peaks and impulse, time over a declared
load budget, escaped mass, simulation time and measured wall cost. Distinguish sensor
forces from raw generated reaction forces, and generated forces from delayed applied
feedback. Do not treat the evaluation load budget as a machine safety rating.

## Admissible claims today

You can report that an algorithm achieved specific outcomes on this pinned discrete
testbed under the stated conditions, including its numerical limitations. You cannot
infer real-excavator performance, physical force accuracy, or safety from these runs.
Contact and terrain refinement currently fail qualification; physical comparisons
remain development evidence. Consult `VALIDATION_STATUS.md` and the evidence manifest.

Before claiming physical transfer, resolve the numerical operating envelope, freeze
calibration and acceptance criteria, admit independent measured trials with uncertainty,
and pass the corresponding held-out comparisons. Visual plausibility is not that test.
