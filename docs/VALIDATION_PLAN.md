# Validation plan and public experimental data

Status: mandatory implementation specification, 2026-09-17. Implementation has started. No dataset has yet been fully downloaded, audited, imported, or replayed in this project. No simulator has passed physical validation. This document is part of SCOPE.md and defines how validation evidence is admitted and used. Full probing/QAM studies are separate experiments; their relevant controls apply when making those research claims.

## Claims and evidence

Create a coverage matrix linking each intended scientific claim to the physical mechanisms, observables, fixtures, data, numerical checks, and acceptance criteria it requires. Record each entry as pass, fail, or not assessed, with reasons and immutable evidence references. Require only relevant physics for a given claim; unsupported physics limits the claim rather than silently becoming an approximation.

Keep three assessments distinct:

- Numerical verification: software and discretization checks on simulated fixtures.
- Physical component validation: agreement with independent measurements for a specific tool/material/motion/observable range, including motion-replay experiments.
- Integrated physical validation: agreement for the complete machine, sensing, actuation, and feedback loop within a specified use and scale.

Physical component validation is legitimate even if integrated validation is still pending. Passing several components does not automatically validate their coupling or a new policy's real-world performance. A run with supported features can still lie outside the validated parameter range.

## Public-data shortlist

Sources were inspected online during project scoping. Listed files and author descriptions establish candidate availability, not completeness or successful reproduction. Pin an actual release/commit and data checksums when admitting a source.

| Candidate | Availability observed | Proposed role | Admission questions and limits |
|---|---|---|---|
| [Robotic Rheometer](https://github.com/johnruck-sed/GRL_2023_RobotRheometer), [laboratory files](https://github.com/johnruck-sed/GRL_2023_RobotRheometer/tree/main/lab_data) | Public laboratory and field CSV/text data and processing code; [paper](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023GL106468) describes robotic intrusion | First candidate for penetration resistance | Audit channel definitions, force inference, tool geometry, packing/preparation, repetitions, and reuse rights. Start with a laboratory subset compatible with the initial material model; field soils do not automatically fit the same constitutive assumptions. |
| [DDBot](https://github.com/IanYangChina/DDBot-IEEE-TRO-2025), [paper](https://arxiv.org/html/2510.17335v2) | Public sand/soil point clouds and heightmaps, camera calibration, and documented trajectory assets; paper describes distinct parameter-fitting and validation trajectories | First candidate for terrain response after prescribed digging | Verify tool geometry, initial state, trajectory availability and timing, and planned versus measured motion. Identify actual physical outcomes separately from manually created task goals and simulated outputs. Surface evidence does not validate forces. |
| [Soil-bin tool-force dataset](https://data.mendeley.com/datasets/4wfc8vh9n7/1) | Published experimental force results and analytical predictions in spreadsheets; record states CC BY 4.0 | Additional cutting-force conditions if compatible | Separate measured columns from predictions. Account for flexible tool supports, tool shape, moist loamy sand, preparation, and whether samples are aggregates or time series. Admit only conditions representable by our backend. |
| [Wheel-loader reality-gap study](https://link.springer.com/article/10.1007/s11044-024-10005-5) | Paper available; normalized time series offered upon request | Later full-size comparison if adequate information becomes available | Not a confirmed public download. Need physical units or normalization constants, geometry, machine/control metadata, initial terrain, and permissions. Normalized curves alone cannot establish absolute load accuracy. |

Inspect the laboratory rheometer subset first, then DDBot sand. Keep these as separate material-specific validations unless evidence supports a shared parameterization; they are not measurements of the same physical soil. Do not contact authors without user authorization. A request-only source cannot be a hidden dependency of the initial public-data path.

## Dataset admission gate

Before fitting parameters, produce a data audit containing:

1. Source DOI/URL, version/commit, license and redistribution terms, checksums, and measured-versus-derived-versus-synthetic labels.
2. Actual file inventory, trial IDs, number of independent preparations/runs, missing channels, units, timestamps, frames, force/torque reference points, and sensor definitions.
3. Tool/container geometry, initial surface and packing information, material preparation, motion/speed, boundary conditions, and physical scale.
4. Measurement calibration, zero offsets, uncertainty/repeatability, filtering, force-estimation assumptions, dropped samples, and any channel saturation.
5. A reconstruction plan identifying supplied quantities, inferred quantities, uncertain quantities, and critical missing quantities.
6. Calibration/development/validation partitions by whole trial, preparation, motion, or condition; no random timestamp splitting of one experiment.
7. Supported claims and explicitly unsupported claims, with admission result: suitable, suitable with stated uncertainty, or insufficient for the proposed use.

Critical missing inputs remain missing; do not fit unrestricted nuisance parameters until a trial appears to match. Geometry reconstructed from figures, digitized curves, or commanded trajectories can support qualified comparisons if uncertainties are assessed, but they do not become raw measured ground truth.

Use calibration data and apparatus metadata to define synchronization and registration. Freeze that procedure before validation. Do not optimize a time warp, amplitude scale, surface registration, or force offset separately on each held-out outcome to hide timing or magnitude errors. Any justified preprocessing is versioned and applied consistently.

Reproduce a representative published measurement or plot from the raw data before using it as a reference. Preserve the raw files; write transformed data separately with a recorded processing chain. Do not execute third-party scripts blindly. Validate the project's loader and metric calculations using independent small cases.

## Replay harness

Each admitted trial becomes an experiment specification containing geometry, material preparation or its uncertainty distribution, initial state, boundary conditions, timing, prescribed inputs, measured outputs, and comparison definitions.

### Motion replay

Prescribe the measured tool pose over time and predict reaction loads and terrain changes. If only planned motion is available, identify it explicitly and assess tracking uncertainty. This validates material/tool response conditional on the motion. It does not validate actuator tracking or closed-loop behavior.

### Command replay

Apply recorded actuator commands through the modeled actuation and predict motion, loads, and terrain. This requires enough machine and controller information to reproduce the input path. Replaying a recorded command sequence is open-loop input replay; it is not a new closed-loop controller test.

### Closed-loop comparison

When physical data supports it, run the corresponding controller against simulated sensor feedback and compare independent physical trials of that feedback-controlled system. Identify which sensing, actuation, and latency assumptions are measured versus approximated. A new learned policy may require new physical trajectories to validate its operating regime.

Match the observation process: compare simulated visible surfaces to the measured camera coverage and comparable spatial resolution, not privileged complete geometry to an incomplete scan. Compare load channels at matching reference frames, bandwidth, and tare conventions. If measured actuator effort includes inertia, gravity, payload, and friction, either model that total or justify the separation into soil load.

### Calibration and held-out evaluation

Use a bounded, identifiable parameter set. Share material parameters across trials of the same preparation; represent measured preparation differences explicitly. Inspect parameter sensitivity and retain plausible alternative fits when different parameters explain the same calibration observations. Compare their held-out predictions. Recovering a unique soil coefficient is not required when only response prediction is identifiable.

Freeze the selected model, parameter-estimation procedure, preprocessing, metrics, and acceptance criteria before final evaluation. Real-data model-validation splits and policy-training/evaluation splits are separate manifests. Repeated use of a validation set for model development requires reclassification as development data and a fresh holdout for a new independent validation claim.

Output raw comparison curves, per-trial errors, group summaries, intervals, failures, and provenance. Compare force direction/components, peaks, timing, work, surface change, and payload only where supported measurements exist. Aggregate force means cannot validate transient peaks; final surface scans cannot validate the entire deformation history. Assess equivalence against useful predefined tolerances, rather than interpreting failure to detect a difference as proof of agreement. No universal 5% or 10% passing threshold is assumed.

## Additional gaps that the core fixtures must address

| Gap | Required verification or validation activity | How it limits claims |
|---|---|---|
| Preparation and internal soil history | Settling/preparation protocol; repeated probe, unload/reload, re-dig, and dig-after-dump sequences; retain relevant internal state | Single fresh-soil scoops do not establish multi-scoop behavior or adaptation to disturbed soil |
| Cumulative error | Repeated excavation cycles without resetting soil; track mass, payload, terrain drift, load/work statistics, and boundary accumulation | Short replay accuracy does not establish long-horizon terrain prediction |
| Actuation and payload coupling | Empty and loaded joint tests; saturation, lag, limit behavior, and gravitational/inertial payload loads | Soil-only validation cannot establish machine timing, effort, or control performance |
| Measurement realism | Frame/tare/filter/timestamp checks; visibility and uncertainty; distinguish ideal wrench from pressure-derived load | A policy using inaccessible or unrealistically clean signals may not transfer |
| Integration and numerical artifacts | Coupling-step refinement, repeated contact, multiple contact bodies, grid-relative translations/rotations in equivalent scenes, and batch/order invariance within tolerances | Correct isolated solvers do not establish correct coupled behavior; a grid direction can become a policy shortcut |
| Operating-range coverage | Record the speed, depth, orientation, tool scale, packing/material range, and sequence histories covered by physical trials; compare learned-policy visitation | An optimizer may select valid simulated actions outside all physical evidence |
| Material-specific calibration | Check behavior across multiple motions under shared parameters and uncertainty; preserve alternate fits | Matching one curve can conceal wrong physics or non-identifiable coefficients |
| Obstacles and shared terrain | Dedicated obstacle/tool and two-tool fixtures; physical evidence required for related physical claims | Separate penetration/deformation data does not validate buried-rock events or cooperative digging |
| Probe causality | Match physical probe trajectories while withholding probe-derived information from a control policy; equal task budgets and physically matched starting states | A probe can loosen soil, so better digging alone does not demonstrate value from information |

The listed verification fixtures are mandatory for applicable initial capabilities. Independent physical checks are required for the corresponding physical claims; when data does not cover a behavior, the report marks it unvalidated. Do not expand initial scope to every soil regime merely to fill every cell. Cohesive/wet behavior, chassis stability, and full-size hydraulics remain outside scope until specifically implemented and validated.

For the probe-causality control, match the physical pre-dig world state across observation conditions using supported snapshots or reproducible paired sequences. Specify exactly which probe observations are withheld, prevent their recovery through recurrent state or privileged channels, and document remaining information in the post-probe scene. Report both the total practical benefit of probing and the narrower effect attributable to the declared information channel. The latter does not follow automatically from the former.

For policy coverage, tag episodes or trajectory segments that leave the tested operating envelope and report their frequency and outcomes. Use declared bounds and observable summaries, not an unsupported promise of perfect out-of-distribution detection. Adversarial simulation stress tests can find defects beyond the envelope; they cannot supply missing physical evidence there.

## Admission and release deliverables

During feasibility, audit both first-choice public sources and choose a physically reconstructable subset. If a source fails, record the blocking metadata and evaluate a suitable alternative before relying on it. Select the initial material/tool fixture using the available evidence as well as compute feasibility.

For admitted sources, the initial implementation must include a loader, matched fixture, frozen splits, calibration configuration, replay command, independent comparison metrics, and an executed report. A generic empty import interface is insufficient. The target is at least one force-response comparison and one terrain-response comparison; failure to obtain suitable evidence for either is a visible unmet target, not a fabricated pass.

Executing these comparisons completes the evaluation work; passing physical acceptance remains outcome-dependent. Report failed comparisons and the resulting limits. The software release may still be useful for simulation research, but failed physical gates prevent the related validity claim. If a physically validated release is the requested deliverable, those failures remain blockers to that deliverable.

Before release, a researcher should be able to reproduce one held-out comparison from pinned source data in a clean environment using the documented commands. Also provide the full coverage matrix, immutable raw-data references, preprocessing provenance, rejected-data notes, open physical-data needs, and scope of every passing claim.

The initial replay evidence cannot establish integrated autonomous excavation, real-machine stability, fuel consumption, rare-event reliability, or fleet coordination without the additional measurements those claims require.
