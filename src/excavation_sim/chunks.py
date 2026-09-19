"""Bounded action-chunk execution with explicit interruption and executed-action logging."""

from collections import deque
from dataclasses import asdict

from excavation_sim.core import JointCommand, ToolCommand


class ChunkExecutor:
    def __init__(self, planner, neutral, max_horizon=32):
        if not isinstance(neutral, (JointCommand, ToolCommand)):
            raise TypeError("declare a neutral command of the backend's action type")
        if type(max_horizon) is not int or max_horizon < 1:
            raise ValueError("positive chunk horizon required")
        self.planner, self.neutral, self.max_horizon = planner, neutral, max_horizon

    def reset(self, seed):
        self.planner.reset(seed)
        self.pending = deque()
        self.events = []

    def interrupt(self, tick, reason):
        self.events.append(
            {
                "tick": tick,
                "event": "interrupted",
                "reason": reason,
                "discarded_actions": len(self.pending),
            }
        )
        self.pending.clear()

    def act(self, observation):
        if not observation.sensor_valid:
            self.interrupt(observation.tick, "invalid sensor packet")
            return self.neutral
        if not self.pending:
            chunk = list(self.planner.plan(observation))
            if not 1 <= len(chunk) <= self.max_horizon or any(
                type(command) is not type(self.neutral) for command in chunk
            ):
                raise ValueError("invalid action chunk length or representation")
            self.events.append(
                {
                    "tick": observation.tick,
                    "event": "planned",
                    "commands": [asdict(c) for c in chunk],
                }
            )
            self.pending.extend(chunk)
        return self.pending.popleft()
