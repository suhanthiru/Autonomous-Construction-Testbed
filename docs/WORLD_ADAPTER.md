# Reusable world and recorded policy execution

The experimental `NewtonToolWorld` implements reset, step, diagnostics, and close.
It uses the same box/soil geometry as the feasibility fixture, but its controller
holds a three-dimensional force command over each 20 ms action. Total resultant
actuator force is capped at 60 N, including gravity compensation. Solver ticks are
2.5 ms. This controller configuration requires its own numerical assessment.

```sh
python scripts/run_tool_episode.py --actions 100 --inspect --output runs/tool-probe-demo
python scripts/check_world_reset.py
python scripts/check_excavator.py
```

`experiments/tool_probe.py` is an external policy example; the simulator package
never imports it. The runner explicitly loads the selected local policy. Observations
contain pose, velocity, and action-averaged generated soil reaction force. The lagged
coupling limitation still applies. Diagnostics and inspection snapshots are privileged.

The optional HTML inspection artifact provides offline orbit/zoom, playback, pause,
single-step, and playback reset. It displays a sampled particle cloud and tool center,
not full collision geometry. It is an early inspection view, not the finished live
excavator viewer. Playback never steps physics. HTML templates ship with the package.

Reset reconstructs the solver and its hidden state. Same-device tests produced zero
position/force differences across two identical five-action sequences, with and without
soil. Advancing one of two worlds left the other's particles and body poses unchanged.
Those results are preserved in `evidence/world-adapter/reset-isolation.json`; they do
not imply cross-device determinism, checkpoint fidelity, or physical validation.

Particle finiteness and escaped mass are reduced on the GPU. The escape envelope is
|x| and |y| <= 1 m, -0.04 <= z <= 1 m; it is an audit region, not a container. Particle
arrays are copied to the host only for explicit inspection. Collider impulse arrays
are currently copied for force observation; this cost remains to be benchmarked.

The procedural machine asset defines slew, boom, stick, and bucket joints at bench
scale, with explicit limits and an open four-wall bucket. An empty-machine fixture
runs for one second. Its simple position servo has a 0.194 rad final boom offset under
gravity; this is not a tracking pass. Coupled machine/soil integration and bucket
retention/dumping remain pending. The asset is original primitive geometry, not a
commercial excavator model or validated machine parameterization.
