# Development workflows

These commands exercise implemented components. The initial release is incomplete:
scripted excavation has not yet succeeded, and physical validation has not passed.

## Live inspection

```sh
python scripts/serve_sim.py --output runs/live-session
```

Open http://127.0.0.1:8766. Step advances one policy action; Play repeatedly advances
physics; Pause stops requesting steps. Manual mode sends the four normalized joint
velocity sliders. Reset creates a new recorded episode. Stop session closes the
recording and server. Orbit and zoom do not advance physics. This view is privileged
and must not be used as a policy observation channel.

Step, reset, manual control, and clean shutdown were exercised through the browser.
A clean stop marks the current episode interrupted, not task-successful. A forcibly
killed process can leave no outcome file; such recordings are not admitted for training.

## Headless recording and typed loading

```sh
python scripts/run_tool_episode.py --machine --policy experiments/excavator_scripted.py --policy-class ExcavatorPolicy --world-config configs/machine-development.json --actions 1200 --task deposit --inspect --output runs/development-episode
```

`excavation_sim.episodes.load_episode(path)` returns typed policy-facing transitions.
It validates action representation, finite observations, time progression, the complete
observation chain, and final tick. It never opens privileged evaluation data. Numerical
failures and interrupted recordings are rejected unless explicitly requested for inspection.

## Sensor configuration

Add `--sensor-config configs/sensors-delayed.json` to the headless command. Sampling
and latency are configured as integer multiples of the action period. Capture tick,
age, and validity are explicit. Initial packets are invalid until the first delayed
sample arrives; the provided policies hold zero commanded velocity during that window.
Noise has independent reproducible random streams per channel. Task evaluation still
uses the underlying uncorrupted observation, not sensor noise as apparent progress.
Surface visibility measurements remain unimplemented.

## Baseline training

```sh
python experiments/behavior_cloning.py runs/development-episode --output runs/bc-model
python scripts/run_tool_episode.py --machine --policy experiments/behavior_cloning.py --policy-class ClonedPolicy --policy-kwargs runs/bc-model/policy-kwargs.json --actions 1200 --task deposit --output runs/bc-evaluation
```

The baseline is deterministic linear ridge regression on time, tool pose/velocity,
force, and joint position/velocity. It does not consume evaluator-only mass or material
properties. Checkpoints use non-pickled NumPy arrays and an explicit feature schema.
Training records whole-episode hashes, fit error, runtime, and provenance. A completed
simulation may have failed its task; this is stated explicitly in training reports.

A development checkpoint was fitted to the cutting-edge episode and evaluated closed
loop for 27 seconds with delayed, noisy sensors. It deposited zero material and failed
the task. This checks the full training/checkpoint/loading/feedback path; it is not a
successful excavation baseline or independent research result. Stronger demonstrations,
frozen scenario splits, and uncertainty/robustness studies remain required.

Offline viewers sample display frames at 10 Hz and round displayed geometry to five
decimal places to keep long replays manageable. Full-rate transition records and
evaluator measurements are not decimated. Playback uses recorded timestamps.

## Reproducible software check

```sh
python scripts/check_software.py --output runs/software-check
```

This records lint, CPU tests, package build, and an isolated base-package installation
with viewer asset checks. Install the pinned `dev` extra first. The output directory
must be new. It does not install optional GPU dependencies into the clean environment
or claim GPU integration or physical validation.

The cutting-edge development policy (`experiments/excavator_edge_cut.py`) completed
27 simulated seconds and deposited 0.4224 kg with zero recorded escaped mass. It
failed the unchanged 0.5 kg deposit goal. The source tree changed during that run;
the pinned manifest and result summary are retained in the machine-development
evidence directory. This is development evidence, not a frozen benchmark pass.
