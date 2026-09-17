# Modular excavation research platform

Status: implementation started, 2026-09-17. The stable testbed is the primary deliverable. Core interfaces and recording are being implemented; coupled physics and physical validation remain unverified. Engine selection, numerical tolerances, and compute budgets remain subject to the feasibility measurements below. The end-to-end completion contract below defines the platform release; complete research studies are separate deliverables.

## Research purpose

Build a reproducible experimental platform for studying how robots manipulate changing terrain under partial observability. A reference research question is whether interaction history and deliberate probing improve excavation in unfamiliar ground under a fixed time, interaction, and mechanical work budget. This question exercises the platform; platform completion does not depend on conducting every proposed study or finding that probing improves performance.

Later experiments should be able to replace policies, inference methods, learned dynamics, tasks, sensors, robot embodiments, and supported physics configurations without modifying unrelated modules. New physical phenomena can require backend work and new validation. Modularity does not imply that every solver supports every experiment or that numerical parameters transfer between solvers.

Credibility has three separate requirements: correct software, verified numerical behavior, and physical validation against independent measurements. An experiment entirely in simulation can establish behavior within the tested model family; it cannot establish transfer to real soil or real excavator safety.

## Initial scope and assumptions

Assume one developer, local simulation execution, and no personally collected physical data initially. Public experimental datasets are now a required validation workstream, subject to the admission audit below; their completeness and applicability are not yet established. The user has a workstation with an RTX 3080 Ti available if the laptop is insufficient. Target that workstation for the first GPU physics benchmark; verify its actual VRAM and software environment during setup. Do not assume an operating-system migration, cloud budget, or physical test access.

Develop contracts, datasets, and CPU tests on the laptop as practical. Start coupled physics with one local soil domain and a small batch on the workstation. Determine particle/grid resolution and batch size from peak-memory and throughput measurements; do not promise thousands of simultaneous excavation worlds on this hardware.

The first complete environment contains:

- One excavator with a fixed chassis and four controlled joints: slew, boom, stick, and bucket. Machine parameters, joint limits, inertias, collision shapes, and asset provenance are explicit.
- A bounded three-dimensional soil bed, a receiving area, and one initially noncohesive material family. Material variations remain within a declared model envelope. The domain is sized after measuring resolution and boundary sensitivity.
- Force-limited joint actuation with response lag and command saturation. This is an actuator approximation, not a validated hydraulic model. Soil resistance must affect motion.
- Probe, scoop, and deposit tasks sharing one world implementation. Probe-then-scoop is the first research benchmark.
- Timestamped joint observations, an explicitly idealized or noisy load channel, and local surface measurements with visibility masks. Ground-truth terrain and material properties remain evaluator-only unless an experiment is explicitly labeled as an oracle.
- Scripted control, trajectory recording, headless execution, inspection playback, reset, and versioned experiment manifests.
- One dynamic rigid obstacle scenario after soil-only coupling is verified. An anchored obstacle is a separately labeled condition.

Chassis driving, track-soil interaction, tipping claims, full hydraulic circuits, saturated soils, rock fracture, photorealistic perception, and autonomous fleet planning are later capabilities. Fixing the chassis prevents claims about machine stability even if the arm dynamics are accurate.

## Architecture and ownership

Use a small Python package with explicit typed interfaces and configuration. Keep GPU computation inside a backend; do not move complete particle states through Python or copy them to the CPU on every step. A small CPU fixture supports interface tests without GPU dependencies.

| Component | Owns | Contract and boundary |
|---|---|---|
| Scenario | Initial geometry, robot instances, material regions, targets, randomization | Versioned specification compiled by a backend; seed streams are independent |
| World backend | Physical state, rigid/soil coupling, contacts, integration | Reset, advance, query, snapshot capabilities, and numerical diagnostics |
| Robot and actuator model | Embodiment, limits, command interpretation, controller state | Converts timestamped commands into physical actuation; exposes machine metadata |
| Sensors | Sampling, visibility, filtering, latency, noise | Observation packets with frame, units, capture/delivery time, validity, and age |
| Task | Goal, reward terms, success and episode conditions | Reads transitions; cannot secretly edit dynamics during reward calculation |
| Policy and estimator | Action selection, memory, belief state, optional learned predictor | Consumes declared observations and goals; resets independently of world physics |
| Evaluator | Independent measurements, ground truth, benchmark splits | Privileged access never travels in ordinary policy observations or training info |
| Recorder | Transitions, diagnostics, metadata, optional native snapshots | Schema version, asset hashes, source revision, dependency lock, backend config |

The backend is responsible for a complete coupled physical step. A soil material implementation can be replaceable inside that backend, but arbitrary rigid and soil solvers are not assumed composable. Supported combinations are registered and tested explicitly.

The public API specifies SI units, a right-handed world frame with Z up, explicit frame transforms, quaternion ordering, force/torque reference points, array shapes, agent identifiers, and numerical precision. These conventions are tested at adapter boundaries.

Stepping follows one documented order: collect simultaneous agent commands, validate and apply actuator limits, advance coupled physics through substeps, capture/deliver due sensor samples, evaluate task outcomes, and record the transition. Rendering does not advance simulation time. Action duration, policy frequency, sensor frequencies, and solver time step are separate configuration values.

An action specifies its interpretation and duration. The first policy action is normalized joint velocity targets passed through force-limited actuators. Torque control and tool-space control are explicit adapters with different experiment identifiers. Learned action chunks run through a common executor; interruption rules and actual executed commands are logged.

A backend capability manifest declares supported materials, dynamic obstacles, reaction loads, multiple interacting tools, batch isolation, selective reset, observation queries, checkpoint fidelity, and device support. Missing required capabilities stop configuration validation. A heightfield implementation cannot silently stand in for three-dimensional granular flow.

## Physics strategy

Start with a small bucket/soil fixture before importing a complete excavator. Verify the open bucket collision geometry, material retention, load transfer, and emptying. A convex hull that fills the bucket cavity or a thin wall that leaks material can invalidate the entire task.

Provisional first candidate: Newton with a rigid articulation solver and implicit MPM, using a pinned release or commit. Its documentation describes granular/elastoplastic material support and provides an explicit example feeding soil impulses back into rigid bodies. These capabilities make it worth testing; they do not establish excavation accuracy. Isaac Lab integration can follow if it improves training or sensing without compromising the validated stepping path. Its current documentation labels MPM as an experimental specialist path.

If the first candidate fails a concrete requirement, evaluate one alternative against the same fixture. Genesis is an alternative with documented rigid/material coupling. Chrono DEM is a possible granular comparison or fallback, especially for grain/contact questions. Do not implement three production adapters at once.

Two model levels are useful over time:

1. A transparent reduced model for interface development and inexpensive training. A mass-accounted heightfield with an explicit resistance law is a possible implementation. Its supported phenomena and empirical assumptions are documented.
2. A coupled three-dimensional material model for the first serious interaction experiments. Its additional numerical detail does not make it ground truth; calibrate and validate it independently.

The reduced model is optional if the primary backend is fast enough. Training speed must be measured before choosing this extra implementation work. Cross-backend evaluation maps common measurable quantities and independently calibrated material behavior, not identically named coefficients. Native checkpoints stay backend-specific; scene specifications and aggregate measurements are portable.

A learned world model is normally a policy-side predictor. A learned physics residual is a separately versioned backend variant trained on a declared calibration split and evaluated against an independent reference. Never evaluate a residual against itself and interpret agreement as validation.

## Physics verification and validation

For each benchmark, publish geometry, material preparation, boundary conditions, solver settings, observables, tolerances, and the evidence that set those tolerances. Freeze acceptance thresholds before comparing learning methods. Unknown tolerances remain explicit decisions; arbitrary percentages are not validation.

| Fixture | Main measurements | Failure it detects |
|---|---|---|
| Empty bucket motion | Tracking, saturation, inertial load | Incorrect embodiment or actuation |
| Settling and pile formation | Mass, settled shape, surface angle | Material loss, unstable preparation, inappropriate material response |
| Plate or tool penetration | Force versus depth and speed, work | Unphysical resistance or force convention |
| Bucket drag | Load profile, displaced mass, final surface | Incorrect cutting response and coupling |
| Scoop, lift, and dump | Retained/deposited/spilled mass, load over time | Bucket leakage, false capture, missing payload forces |
| Obstacle contact | Impulse, penetration, obstacle motion, actuator response | One-way coupling and invalid obstacle behavior |
| Two tools sharing soil | Loads and material movement with agent order permuted | Sequential-agent artifacts and double counting |
| Repeated probe and re-dig | Response after disturbance, unloading, and redeposition | Missing soil history and incorrect adaptation cues |
| Multi-cycle excavation | Accumulated terrain, mass, work, and payload errors | Long-horizon drift hidden by fresh-soil resets |

Repeat selected fixtures at smaller time steps, finer spatial resolution, and enlarged domains. Check whether relevant measurements converge sufficiently for the claimed effect size. Examine work and momentum accounting, including support reactions and dissipative losses, rather than requiring energy conservation from dissipative soil.

Track total material mass and all exits or transfers. Volume is not conserved when packing density changes. Particle deletion, numerical clamping, failed solver convergence, and capacity overflow are recorded as numerical events and can invalidate a run. A physically correct task failure remains in benchmark statistics; simulator failures are reported separately and never silently dropped.

Use physical measurements when available: a soil bin, known bucket geometry, calibrated load sensing, measured trajectories, and before/after mass and surface measurements. Calibration and validation use different trials and conditions. A small rig supports claims at its tested scale; excavator-scale transfer requires additional evidence. Literature data can help only when geometry, preparation, units, and use rights are adequate.

### Mandatory evidence for trusting a result

Trust is specific to a proposed use. Before an experiment is accepted, identify its quantities of interest, relevant physical conditions, required accuracy, and which validation evidence supports them. A backend that supports an API is not automatically physically validated for that use.

The validation process must cover five distinct questions:

1. Implementation verification: are units, geometry, interfaces, accounting, and state transitions correct?
2. Numerical verification: are relevant measurements sufficiently insensitive to discretization, solver settings, domain boundaries, and execution configuration?
3. Physical validation: do predictions agree adequately with independent measurements in the stated operating envelope?
4. Exploit resistance: can learned or adversarial actions exploit nonphysical behavior or reward-accounting defects?
5. Conclusion robustness: can plausible numerical, physical-model, sensor, or actuator uncertainty materially change the experimental conclusion?

Implement a versioned acceptance specification for each fixture and research benchmark. It records observable definitions, dimensional units, aggregation, acceptance bounds, uncertainty treatment, reference provenance, applicable geometry/material/speed ranges, and required repetitions. Choose thresholds from measurement quality and the intended effect size using development data, then freeze them before final comparisons. A release cannot pass with required tolerances still marked TBD.

Physical component validation can use prescribed-motion tests to isolate soil response. Claims about the integrated sensor/controller/actuator/soil loop additionally require feedback-controlled physical comparisons. Agreement on one commanded trajectory does not establish correct closed-loop behavior. Assess force profiles, peak loads, work, retained/deposited mass, final surface shape, and repeatability as relevant; one aggregate fitting score cannot replace these measurements.

Keep calibration and validation trials separate. Record material preparation, initial packing, moisture when relevant, geometry, measured motion, sensor calibration, and experimental uncertainty. Reusing validation trials to tune the model moves those trials into development data and requires a fresh validation set for an independent claim.

Discretization studies compare task-relevant aggregate observables and their variation rather than requiring individual grains to follow identical paths. Changing the timestep, resolution, domain size, solver tolerance, or batching strategy must not produce an unexplained change large enough to undermine the claim. If no stable regime is identified within the available compute, report that limitation and withhold the affected claim.

Propagate supported uncertainty in material behavior, actuator response, sensing, and model discrepancy through the comparative evaluation. Report the distribution of the difference between methods, including sensitivity of their ranking. If uncertainty bounds have no empirical basis, label the work as a sensitivity study rather than a calibrated statement of real-world uncertainty. Another engine is an independent diagnostic, not a substitute for physical measurements.

### Mandatory test suites and execution policy

| Suite | Required checks | Execution and evidence |
|---|---|---|
| Core contracts | Units/frames and wrench reference points; action duration; simultaneous commands; sensor capture/delivery timing; limits; terminal versus timeout handling; invalid capability rejection | Fast CPU checks on relevant changes; machine-readable results |
| State and data integrity | Independent random streams; reset isolation; supported restart fidelity; recorder round-trip; commanded versus executed actions; dataset split membership; hidden-state leakage | CPU checks plus GPU integration where state lives in the backend |
| Coupled physics | All fixtures above, including mass accounting, payload reaction loads, open bucket geometry, obstacle response, and two-tool interaction | Pinned backend and hardware profile; numerical diagnostics and raw measurements retained |
| Numerical sensitivity | Timestep, spatial resolution, domain extent, solver convergence settings, batch isolation, and rendering/headless equivalence | Before release and after relevant physics changes; quantitative comparison against frozen tolerances |
| Exploit and stress | Rapid oscillation, edge scraping, repeated scoop/dump, boundary contact, extreme legal commands, and reset loops; check material duplication, leakage, artificial work gains, and reward shortcuts | Scripted adversarial cases plus inspection of learned-policy trajectories |
| Physical validation | Held-out measured interactions and closed-loop tests with uncertainty and data provenance | Required for each physical-validity claim; missing data is explicitly not assessed |
| Research evaluation | Budget matching, independent training repeats, locked scenarios, ablations, failures, statistical uncertainty, and sensitivity of conclusions | Full initial benchmark and each published comparison; full cost accounting |
| Reproducible installation | Clean supported environment, dependency lock, asset availability, demo, data generation, checkpoint evaluation, and report regeneration | Release gate with exact commands and logs |

Required checks return pass, fail, or not assessed, with a reason. A skipped GPU test is not a pass. CPU CI can run without a GPU; the full release additionally requires recorded execution on available GPU hardware. Missing hardware leaves the relevant gate pending. Store the tested configuration and software versions with each result. Re-run affected suites after changes; unrelated edits do not require repeating every expensive experiment.

Use independent references where feasible: analytic rigid-body cases, measured fixtures, and separately calculated mass/work accounting. Avoid tests that merely reproduce the implementation's formula. Preserve representative failures as regression fixtures. Numerical failures have explicit diagnostics and follow a predeclared retry/exclusion policy; publish their frequency and prevent silent success-only summaries.

### Validation report and extension assessment

Each release includes a readable validation report and a machine-readable manifest linking tests to evidence. Both state the release/backend/assets/hardware versions, tested operating envelope, measured errors, numerical sensitivity, empirical data coverage, known failures, and supported or unsupported claims. An evidence table must distinguish software checks, simulated stress tests, and independent physical measurements.

Each new experiment declares required physical capabilities and observables. Its assessment references existing evidence and identifies missing checks. A policy-only change reuses physical evidence but still receives exploit, budget, and conclusion-robustness checks. A new material, embodiment, sensor model, contact method, or learned physics residual triggers validation for the affected behavior. Reusing a validated component in a new coupling requires an integration assessment.

Changes to physics or measurement definitions create a new benchmark version when they can change results. Preserve old configurations and reference outputs; never overwrite a published baseline silently. Tests and reports stay tied to the exact tested release.

### Public experimental replay and remaining coverage gaps

The [validation plan](docs/VALIDATION_PLAN.md) is a mandatory part of this scope. It defines dataset admission, replay modes, fitting and holdout rules, comparison reports, and the physical evidence required for each claim.

Audit the public Robotic Rheometer laboratory data for penetration resistance and DDBot sand data for terrain deformation first. Evaluate the published soil-bin force dataset as an additional candidate where its material and tool compliance fit our model. The wheel-loader study offers normalized series on request and is not an assumed public download. Confirm source files, metadata, licenses, physical provenance, and reconstructability before admitting any dataset. Full audits and replay runs have not yet occurred.

Required workflow: preserve and identify raw measurements; reconstruct the apparatus at its original scale; reproduce a source measurement with the loader; calibrate on selected whole trials; freeze preprocessing, parameters, and thresholds; replay held-out motions; report errors, uncertainty, and failures. Distinguish measured trajectories from planned commands, physical outcomes from desired target shapes, and measured forces from analytical predictions.

Motion replay tests soil response conditional on tool motion. Command replay tests predicted response to recorded commands and remains open-loop input replay. An integrated closed-loop claim requires the corresponding controller to operate on simulated feedback and independent physical evidence of that feedback-controlled system. No form of recorded replay alone establishes that a new learned policy will work physically.

The first release must audit the selected sources and execute matched comparisons for admitted subsets. Target at least one force-response and one terrain-response comparison. If suitable data cannot be admitted, record the unmet target and required missing evidence; do not replace it with synthetic ground truth. Running a comparison is a deliverable; passing its physical criteria is a separate, outcome-dependent claim.

Additional mandatory checks cover repeated soil disturbance, cumulative multi-scoop error, actuator/payload feedback, sensor bandwidth and visibility, grid/coupling artifacts, and policy visitation outside validated ranges. Quantify uncertainty in preparation and parameter fitting. Build a claim-to-evidence coverage matrix so a component-level pass cannot silently become full-machine validation.

## Observability and information control

Represent material and obstacle truth in the simulator, then derive observations through the sensor layer. Do not let particle color, segmentation labels, debug overlays, exact underground geometry, scenario IDs, or hidden parameters identify material to a nominally blind policy.

A simulated bucket wrench is initially an ideal sensor. Real excavators may offer different telemetry, so load-estimation and sensor-access ablations are required. Hydraulic pressure is not fabricated from joint torque without an explicit hydraulic model and sensor mapping.

Material identification can be ambiguous: different parameter combinations can yield similar observed forces. The first inference objective is predicting future observable response with calibrated uncertainty, not necessarily recovering every true soil coefficient. Test parameter recovery only in scenarios where it is identifiable.

Sensor outputs include occlusion, freshness, and availability. A heightmap formed from observed surfaces differs from a privileged global terrain query. Both can exist but must have different names and benchmark tracks.

## Reproducibility and datasets

Record the resolved configuration, code revision and dirty patch hash, dependency versions, asset hashes/licenses, hardware and driver details, random streams, scenario split, solver settings, policy checkpoint, controller configuration, and numerical diagnostics.

Each transition includes observations, commanded and executed actions, timestamps and duration, individual reward terms, termination/truncation reasons, and independent evaluation measurements in a separately privileged channel. Store learner-facing datasets without hidden evaluation data. Distinguish mechanical work from hydraulic/fuel energy estimates.

Use chunked array storage for time series and sensor data, plus a JSON manifest and compact episode summaries. Select the concrete storage dependency during implementation. Video supports inspection but is not a substitute for raw observations and transitions.

Exact restart requires soil internal variables, actuator/filter state, delayed sensor buffers, random generator states, and solver history. If a backend cannot restore these, advertise observation playback and seeded reruns, not exact branching. Test reset isolation separately from restart fidelity. GPU reproducibility is measured with declared tolerances; bitwise equality across devices is not assumed.

Scenario generation has separate training, development, and locked test sets. Split across material regimes, geometry families, and preparation conditions as appropriate, not just random seeds. Model fitting, reward tuning, and normalization statistics use training/development data only.

Benchmark reports include independent training runs, per-scenario results, uncertainty intervals, and total compute/interaction cost. Paired test scenarios improve comparisons; evaluation episodes are not substitutes for independent training seeds. Choose replicate counts using pilot variability and the effect size of interest.

## Reference research benchmark

Question: with the same total task budget, does deliberate probing improve excavation under hidden changes in material response?

Use a simple soil family first, then held-out parameter ranges and spatial material transitions. Add buried obstacles as a separately versioned difficulty. A material variation that produces no observable behavioral difference cannot test adaptation.

Compare:

- A scripted controller.
- A reactive learned policy with current observations only.
- A history-conditioned policy with no explicitly prescribed probe phase.
- A fixed probe followed by history-conditioned digging.
- A budget-matched random or uninformed probe control.
- A learned probing strategy.
- A privileged material-aware reference, labeled as privileged rather than a guaranteed mathematical upper bound.

Match demonstrations, training interactions, model capacity where possible, and total evaluation time/work budgets. Charge probe actions against the task budget. Give non-probing controls the same opportunity to use their budget productively. Compare learned probing with fixed or random information gathering so extra interaction alone does not explain gains.

Add an information-withholding control after the same physical probe sequence: the compared policies start digging from matched disturbed-soil states, but one receives the declared probe observation history and the other does not. Prevent hidden history leakage and document information still visible in the final scene. Report the practical benefit of probing separately from the effect attributed to information; soil loosening alone can improve the next scoop. See the validation plan for the paired-state protocol.

Primary measurements: successfully deposited mass per episode and per elapsed simulated time; peak and integrated load-limit exceedance; positive mechanical work; task success; intervention/abort rate; and material loss. Report tradeoffs rather than hiding them in one reward number. Inference quality is measured by future-response prediction and uncertainty calibration on held-out actions.

Ablate force access, history length, probe budget, sensor latency/noise, and physics resolution. Evaluate ranking stability across materially different model assumptions when feasible. Keep offline belief updates distinct from online neural-weight updates and report their costs separately.

QAM becomes a subsequent algorithm experiment using the same transitions, controls, evaluation, and demonstration split. Its exact paper/version and action representation must be specified before implementation. Compare against behavior cloning and an appropriate established RL baseline under matched data and compute budgets.

The platform release must contain a working training/evaluation path, a trained reference checkpoint, and an executed evaluation demonstrating the interface. Use behavior cloning as the demonstration-learning reference; select and pin an additional conventional continuous-control RL example if required to exercise the transition interface. The full comparison above is the protocol for a subsequent probing study. Identify training method and observation access separately, so algorithm changes are not confused with benefits of memory or probing. A privileged reference is clearly labeled and is not described as an upper bound without evidence.

When conducting the probing study, include at least force-access, history, and probe-budget ablations together with the mandatory numerical and uncertainty/sensitivity checks. Record training seeds, failed runs, checkpoint-selection criteria, training interactions, simulated evaluation time, wall-clock cost, and inference cost. A training smoke test alone does not establish a research result. Set the feasible replicate count and budget before the final benchmark and justify them using pilot variance. If the available budget cannot resolve the effect, report an inconclusive result.

Completion requires an honest result, not a positive probing result. Negative and inconclusive results are acceptable research outcomes when the protocol, executed runs, and limitations are complete. A broken training pipeline or unexecuted required comparison is incomplete work.

## Multi-agent extension

From the first architecture, the world owns a collection of robot instances and advances one joint action for all agents. Agents interact through one shared terrain state. Batched independent worlds and several agents in one world are different concepts and different array axes.

Include a small two-tool shared-soil regression fixture before freezing interfaces. A full second excavator, learning algorithm, or fleet workflow is unnecessary for this architectural check.

Later cooperative tasks add local observations, communication budgets, shared/individual rewards, and explicit team termination semantics. A centralized critic can receive privileged training state through a separate interface, while deployed actors remain restricted to their declared observations. This supports future shared-terrain manipulation without promising arbitrary deformable-object tasks from an excavation-only backend.

## Delivery stages and exit conditions

| Stage | Deliverable | Exit condition |
|---|---|---|
| 0: feasibility | Bucket/soil fixture, public-data audit, and backend report | Measured load feedback, retain/dump behavior, numerical sensitivity, memory, speed, reset behavior; reconstructable data subsets identified or evidence gaps recorded; engine selected from evidence |
| 1: contracts | Minimal core, CPU fixture, recorder, scenario validation | Units/frames/time semantics, capability rejection, leakage checks, replay metadata, and independent-world isolation verified |
| 2: physical environment | One fixed-base excavator, one material family, scripted task | Repeatable scoop/deposit; verified actuator limits, mass accounting, solver diagnostics, and declared physical limitations |
| 3: benchmark release | Versioned scenarios, baseline policies, dataset, evaluator | Locked test manifest; reproducible baseline report with failures, uncertainty, and full costs |
| 4: first experiment | Probe/history adaptation comparison | Budget-matched result with ablations and an explicit validity envelope |
| 5: extensions | QAM, learned dynamics, second embodiment, cooperative tasks | Each addition passes relevant contract and physics checks before benchmark inclusion |

Stages 0 through 3 define the initial end-to-end platform release. Stages 4 and 5 are subsequent research studies and extensions. The initial release includes executed training/evaluation and extension examples demonstrating that experiments can be removed without breaking the core simulator.

Stages 0 and 1 inform each other; do not freeze speculative interfaces before the coupled fixture exists. Plan the first feasibility attempt as roughly one to two developer-weeks, an estimate rather than a promise. Re-estimate subsequent work from measured backend integration effort and throughput. A credible research platform is a multi-month effort, with physical data collection potentially determining the critical path.

Measure effective policy transitions per wall-clock second, simulated seconds per wall-clock second, peak VRAM, reset time, observation cost, and recording overhead separately from rendering. For a training budget of N transitions and measured rate R, rollout time is N/R before learning, evaluation, and startup costs. Use this to decide whether a reduced training model or additional compute is necessary.

## End-to-end completion contract

If implementation is requested for this scope, the deliverable is a usable initial research release spanning the complete scenario-to-report workflow. The following are required delivered artifacts, not merely planned interfaces:

| Deliverable | What the user can do | Evidence required for completion |
|---|---|---|
| Installable repository | Install a pinned environment on the supported machine and run documented commands | Clean-environment installation and hardware/dependency check logs; actual supported OS and GPU profile |
| Working 3D environment | Watch a fixed-base excavator probe, scoop, lift, and deposit material; reset and inspect loads and observations | Executed coupled-physics demo, headless equivalent, and supported scenario configurations |
| Inspection viewer | Pause, single-step, reset, change the camera, and show selected sensor/force/terrain overlays | Working viewer; debug truth overlays isolated from policy inputs; recorded example |
| Scenario library | Select material variations, surface geometry, and an obstacle condition; reproduce a named episode | Versioned generators and frozen training/development/test manifests within the supported physics envelope |
| Data workflow | Generate scripted demonstrations, record policy rollouts, load transitions, and replay observations | Versioned dataset schema, provenance, sample dataset, loader, and round-trip verification |
| Baseline learning workflow | Train and evaluate a reference policy through the public experiment interface | Actual reference checkpoint and evaluation outputs; documented budgets and reproducible configurations |
| Evaluation report | Inspect productivity, work, load violations, and task failures | Completed scripted/reference-policy evaluation, numerical sensitivity, costs, and plots generated from retained data; no unsupported comparative research claims |
| Verification package | Run contract, integration, numerical, and adversarial suites | Executed results for mandatory applicable suites, including GPU tests; no skips represented as passes |
| Physical-validation workflow | Import independent trial data, map its units/frames, run matched fixtures, and generate error reports | Public-source audits and executed replays for admitted subsets; target one force-response and one terrain-response comparison; failed or unavailable physical gates explicitly reported |
| Validation report | See exactly which experimental uses are supported by which evidence | Versioned human-readable report and machine-readable evidence manifest; physical data gaps explicitly marked |
| Extension examples | Add a policy and a task without editing unrelated simulator modules; exercise shared-soil interaction | Executed external experiment examples and the two-tool shared-world fixture |
| Handoff documentation | Reproduce results, change configurations, interpret limitations, and add experiments | Quick start, architecture/API guide, benchmark protocol, asset licenses, known issues, and commands to regenerate reports |

The viewer is a research inspection tool. Initial completion does not require a polished web application, custom rendering engine, full fleet simulator, QAM implementation, or a learned replacement for soil physics. Those are later additions with their own experiment and validation requirements.

The expected user workflow is: install/check hardware; open a scripted demo; generate or load demonstrations; train a baseline; evaluate a frozen scenario suite; inspect a failed episode; regenerate the comparison report; replace a policy or task and repeat. Deliver a command for each step and verify the complete sequence. Command names will be finalized in implementation documentation rather than presented here as existing executables.

### Two separate completion claims

**Initial simulation research release:** all applicable software, coupling, numerical, baseline-training, evaluation, documentation, and reproducibility deliverables above are implemented and executed on available supported hardware, including public-data audits and executed comparisons for admitted subsets. Its report can state simulation results and their supporting evidence. Passing public-data comparisons can establish physical component validation within a specified range; failed or missing physical gates remain explicit and integrated real-world validity remains an open milestone.

**Physically validated release for a specified use:** the initial release plus adequate independent measured trials, frozen acceptance criteria for that use, uncertainty assessment, and passing held-out prescribed-motion and closed-loop validation within a named operating envelope. This claim depends on suitable data or physical access and cannot be satisfied by code generation, attractive rendering, synthetic references, or another unvalidated simulator.

The initial release is the implementation target with public experimental data and no assumed physical apparatus access. If passing physical validation is requested as a completion requirement, it remains required work until the necessary evidence is obtained; it cannot be silently waived. Even physical validation for one material, scale, and task does not validate every future experiment.

### Honest handling of resource limits

The 3080 Ti is an available target, not yet a connected execution host. Workstation execution can only be claimed once access and test runs actually occur. Record the laptop's usable hardware during setup, and run locally where possible. Do not claim workstation benchmarks from estimated performance.

Beginning implementation immediately does not remove training time, solver feasibility risk, GPU access needs, or data-collection dependencies. If a required gate cannot be completed, deliver the completed artifacts with that gate explicitly pending and continue authorized independent work. Do not substitute a toy soil animation, an untrained policy, or proposed test commands for the required working system and evidence. Any substantive reduction of the release scope must be explicit.

## Proposed repository layout

```text
src/excavation_sim/
  core/          # contracts, time, units, capability validation
  backends/      # coupled runtime adapters and CPU fixture
  robots/        # embodiment and actuator definitions
  sensors/       # observable channels and timing
  tasks/         # goals, rewards, episode semantics
  scenarios/     # generation and versioned split manifests
  data/          # recording and dataset schemas
  evaluation/    # independent metrics and reports
experiments/     # probing, QAM, world models, multi-agent algorithms
benchmarks/      # physics fixtures and frozen research protocols
assets/         # licensed geometry and provenance
configs/        # resolved and composable experiment inputs
tests/          # contracts, numerical regressions, integrations
docs/           # decisions, calibration reports, limitations
```

Experiments depend on the simulator; the simulator never imports an experiment. Plugin registration starts as ordinary Python factories with typed configuration. Add external package discovery only when external extensions require it. Version benchmark behavior independently from package releases, because a physics fix can change published results even without changing API signatures.

## Decisions needed before implementation

- RTX 3080 Ti workstation is available; verify VRAM and operating system constraints. Cloud compute is not assumed.
- Admission audit of the shortlisted public measurements; additional data or a soil test rig for uncovered integrated physical claims.
- Initial machine dimensions and a usable geometry source; define one physical scale explicitly.
- Acceptable wall-clock training budget and first experiment priority.
- After the fixture: backend/version, spatial resolution, time steps, numeric acceptance thresholds, and supported checkpoint behavior.

## Sources checked for the engine shortlist and validation approach

- [Newton implicit MPM documentation](https://newton-physics.github.io/newton/latest/api/_generated/newton.solvers.SolverImplicitMPM.html): material solver capabilities and configuration. Development documentation can differ from a pinned release.
- [Newton two-way coupling example](https://github.com/newton-physics/newton/blob/main/newton/examples/mpm/example_mpm_twoway_coupling.py): explicit soil impulse feedback to rigid bodies.
- [Isaac Lab physics backends](https://isaac-sim.github.io/IsaacLab/release/3.0.0/source/concepts/physics_backends.html): backend scope and experimental specialist paths.
- [Genesis coupling documentation](https://genesis-world.readthedocs.io/en/latest/user_guide/theory/coupling/index.html): alternative coupled solver implementation.
- [Chrono DEM-Engine](https://github.com/projectchrono/DEM-Engine): granular solver candidate.
- [A multiscale model of terrain dynamics for real-time earthmoving simulation](https://arxiv.org/abs/2011.00459): relevant research precedent for mixed terrain representations; not evidence that the proposed implementation is validated.
- [NASA modeling and simulation validation guidance](https://public.ksc.nasa.gov/mns/faq/): validation and use assessment depend on intended use and documented operating limits. This project adopts that principle; it does not claim NASA certification or formal compliance.
- [NASA Standard for Models and Simulations](https://standards.nasa.gov/node/263): reference for explicit acceptance criteria and simulation credibility practices.
- [Simulation of front end loader bucket-soil interaction using discrete element method](https://experts.illinois.edu/en/publications/simulation-of-front-end-loader-bucket-soil-interaction-using-disc/): experimental comparison of simulated bucket reaction loads, including sensitivity to particle representation.
