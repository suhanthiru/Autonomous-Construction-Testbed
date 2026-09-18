# Shared-soil tool fixture

`NewtonSharedToolWorld` places two independently actuated dynamic boxes in one soil
domain. It reuses the coupled stepping path of `NewtonToolWorld`. Agent IDs are
`tool_0` and `tool_1`; each controls world-frame linear velocity in metres per second.

Call `reset_agents(seed)` and `step_agents(commands)`, where `commands` maps both IDs
to `ToolCommand` values. Missing or extra agents and incorrect command types are
rejected before advancing time. Commands are collected simultaneously and applied
in canonical agent order. Dictionary insertion order does not set execution order.

Each returned observation has the same world tick and contains only that tool's
position, velocity and action-averaged soil force. `agent_loads()` is an evaluator
query for applied actuator forces and generated soil loads. The latter still have
the lagged-coupling interpretation described in the numerical audit. World-level
diagnostics report the total material mass and escaped mass; do not add that mass
once per agent. The legacy single-tool actuator diagnostic names the primary tool;
use `agent_loads()` when assessing both actuators.

Run the explicit GPU component check:

```sh
python scripts/check_shared_tools.py --output runs/shared-tools-check
```

It repeats a two-second contact trajectory after reset with the command dictionary
reversed, checks rejection of incomplete commands, and executes a control where
the second tool is commanded to hold. Full traces and source hashes are retained.
Exact replay agreement is a same-device observation, not a cross-device promise.
The control's aggregate trajectory difference alone does not prove soil-mediated
interaction, because one tool's command was intentionally changed.

This fixture is not two excavators or a validated cooperative manipulation task.
It currently supports whole-world reset, ideal sensors and explicit evaluator
recording through the fixture script. Selective reset, a general multiagent training
adapter, coupled load-budget validation and cooperative task success remain open.

## Executed repeatability finding

Holding the lightweight tools' velocity-servo force for the whole 20 ms action
produced substantial divergence after contact: up to 25.7 mm position difference
and 62.6 N force difference in the first reversed-order comparison. Identical-order
repeats also diverged. Reversing a mapping from the same state produces exactly the
same actuator force buffer, so this is not evidence of sequential agent execution.

The shared-tool servo now updates at each 2.5 ms physics tick. In an unchanged-source
two-second retry, maximum reversed-order differences were 0.116 mm, 0.01594 m/s and
1.052 N. Identical-order repeat differences were 0.079 mm, 0.00611 m/s and 0.472 N.
Both tools contacted soil; no material escaped the declared audit region. The faster
servo substantially reduced observed divergence, but exact replay still failed.
These are measured component discrepancies, not chosen acceptance tolerances or a
physical validation pass. Reports are in `evidence/shared-tools/`.
