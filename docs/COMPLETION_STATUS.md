# Completion status

## Delivered and executed

The operational system runs installation → hardware check → simulation and recording
→ compressed dataset → baseline training → frozen evaluation → report and replay.
The complete frozen run, trained checkpoint, dataset and raw outcome records are in
`evidence/release-v1/`. The repeated excavation demonstration passes the 0.5 kg task
without resetting soil. The learned baseline's failed tasks are retained.

The system also provides live controls, masked terrain sensing, external policies and
tasks, action chunks, named material/terrain/obstacle scenarios, shared-soil tools,
source/configuration hashes, tests and CI. See `REPRODUCE.md` and `API.md`.

New headless episodes, live episodes and evaluation suites capture a checksummed
validation assessment. The optional `--require-passed-gates` launch flag refuses
missing, malformed, failed or incomplete global assessments before loading a policy.
That flag checks recorded assessments; it does not infer that a new experiment lies
inside a validated operating envelope. Existing frozen evidence is unchanged.

## Not complete: numerical and physical qualification

The requested fully validated testbed is not delivered. The present evidence does
not support that claim, even though the software workflow is operational.

| Blocker | Evidence | Requirement to close it |
|---|---|---|
| Contact numerics | Timestep sensitivity persists under prescribed motion; adaptive feedback did not resolve it | Demonstrate a converged configuration for the required motion/load regime, including spatial refinement |
| Terrain numerics | Existing development surface differences are not monotonically decreasing | Resolve preparation/discretization sensitivity and establish a numerical envelope |
| Force physical validation | Published resistance is underpredicted; repeat grouping and uncertainty are unresolved | Admissible independent trials, preparation and measurement uncertainty, frozen calibration and useful acceptance criteria |
| Terrain physical validation | Available replay uses planned motion and inferred initial state | Tracking/preparation uncertainty, frozen calibration/criteria and independent evaluation after numerical gates |
| Integrated machine validation | Procedural bench-scale machine; no matched physical machine trials | Measured actuation, sensing and repeated excavation data for a specified machine/use |
| Shared-soil reproducibility | Same-order contact repeats vary | Characterize and accept a statistical operating envelope or resolve the source of variation |

More code, an attractive replay, or passing software tests cannot supply missing
physical measurements. The current validation command correctly returns nonzero.
The latest isolation evidence is in `CONTACT_ISOLATION.md`; older failed studies
remain available. Neither the completion contract nor its physical gates was waived.

## Launch and inspect

Follow `REPRODUCE.md` for the complete workflow. For ordinary development runs:

```sh
python scripts/serve_sim.py --output runs/live-session
python scripts/run_release_workflow.py --output runs/reference-workflow
```

For a study that requires every recorded gate to have passed, use:

```sh
python scripts/run_tool_episode.py --require-passed-gates --actions 100 --output runs/qualified-study
```

The last command intentionally refuses the current release. It must not be described
as a completed physical-validation milestone.
