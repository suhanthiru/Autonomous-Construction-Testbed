# Simulator and experiment interfaces

## Frames, units and timing

All quantities are SI. The world is right-handed with Z up; transforms use XYZW
quaternions. `Clock` uses integer physics ticks. An action spans a whole number of
physics ticks, and `duration_s` records its actual interval. Policies run at action
boundaries. Sensor sampling/latency are declared multiples of that action period.

`Observation.tool_position_m` is the world position of the tool body origin (the
bucket pivot on the procedural excavator). `tool_velocity_m_s` is the body's COM
linear velocity in world coordinates, following Newton's spatial-velocity convention.
These are different reference points when the COM is offset: the velocity field is
not the derivative of the pivot position under rotation. Joint observations are
ordered slew, boom, stick, bucket, in radians and radians/second. Passive obstacle
coordinates are excluded.

`soil_force_n` is the world-frame generated MPM reaction impulse summed over the
action interval and divided by its duration. It is not the instantaneous applied
force in the lagged rigid/soil coupling, not hydraulic pressure, and not a six-axis
wrench. The current capability is `REACTION_FORCE`; requesting `REACTION_WRENCH`
fails because soil torque is not provided. Earlier development manifests used the
broader name; their recorded values were still three force components.

## World, sensors, policy and task

`World` exposes `reset(seed)`, `step(command)`, `diagnostics()` and `close()`.
`BackendInfo.require()` rejects unsupported requested capabilities. No exact restart
capability is advertised: reset reconstructs the solver and its hidden state.

`JointCommand` holds four normalized velocity targets in [-1, 1]. The motor model
integrates a limited joint reference, uses PD feedback and self-weight gravity
compensation, caps effort, and applies a first-order response lag. This is not a
hydraulic model. `ToolCommand` instead requests world-frame linear velocity for the
box-tool actuator. These are distinct action representations and datasets.

`ObservedWorld` owns the sensor sampling, delay queue and independent noise streams.
`sensor_capture_tick`, `sensor_age_s` and `sensor_valid` travel with the packet.
The optional `SurfacePacket` contains only masked visible column heights; see
`SURFACE_SENSOR.md`. Evaluator access to raw observations is explicit.

An external policy implements `reset(seed)` and `act(observation)`. An external task
implements `reset()` and `evaluate(observation, diagnostics)`, returning `TaskResult`.
The command-line task loader additionally records the task's dataclass `config`.
Tasks do not receive a world reference. `rollout` evaluates the task using raw
measurements, records transitions, and closes the world even on failure. Termination
for task success and truncation for budget exhaustion are distinct. Simulation
completion is also distinct from task success.

`ChunkExecutor` accepts a planner's bounded list of same-type commands. It logs the
proposed sequence, pops one action at each boundary, and discards pending actions
when interrupted or presented an invalid sensor packet. The recorder stores every
executed command independently of the proposal log.

## Privileged evaluation and recording

Policy transitions are in `transitions.jsonl`; evaluator diagnostics are in
`evaluation.jsonl`. Runtime model metadata records the generated masses, inertias,
transforms, audit region and actuator specification. Source identity includes code,
configs, scenario manifests and dependency pins. Checkpoints and extension artifacts
are hashed by the runner/evaluator.

`load_episode` validates completed outcomes, continuity, finite channels, timestamps
and action representations. Interrupted/failed episodes require explicit inspection
access. `packed.export_episode` emits checksummed compressed shards;
`packed.iter_records` reads policy records without opening evaluator data. The sample
dataset preserves its older source identity instead of being relabeled as new evidence.

This separation prevents accidental privileged inputs through the ordinary API. It
does not sandbox hostile Python policies from the filesystem. An intentionally
privileged policy must be labeled as an oracle in its experiment protocol.

## Scenarios and extensions

`Scenario` is engine independent. `NewtonScenarioWorld` compiles the supported
material, surface and obstacle specifications. The suite checksum and split name
are recorded in every named episode. Training with a suite rejects data outside its
declared training split. Unsupported shape types fail the surface sensor explicitly.

`NewtonSharedToolWorld` collects a complete mapping of both agent commands before
advancing the common soil state. It returns observations by stable agent ID. See
`SHARED_TOOLS.md` for measured repeatability limits. This is a two-tool extension
fixture, not an autonomous fleet model.

New physical phenomena require a backend extension, new capability declarations,
and new verification. A new policy or task does not require edits to the integrator.
Behavior-changing physics, observation semantics and scenario edits require a new
benchmark version; preserve prior manifests and outputs for comparisons.
