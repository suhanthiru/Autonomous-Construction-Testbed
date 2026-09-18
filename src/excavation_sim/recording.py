"""Append-only episodes. Privileged diagnostics are written to a separate stream."""

import json
from pathlib import Path
from typing import Any

from excavation_sim.core import Diagnostics, JointCommand, Observation, ToolCommand
from excavation_sim.provenance import canonical_json


class EpisodeWriter:
    def __init__(self, directory: Path, manifest: dict[str, Any]):
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        self._last_tick: int | None = None
        self._closed = False
        (directory / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
        self._transitions = (directory / "transitions.jsonl").open("x", encoding="utf-8")
        self._evaluation = (directory / "evaluation.jsonl").open("x", encoding="utf-8")

    def append(
        self,
        before: Observation,
        command: ToolCommand | JointCommand,
        after: Observation,
        diagnostics: Diagnostics,
        task_result: Any = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("episode is closed")
        if after.tick <= before.tick or after.time_s <= before.time_s:
            raise ValueError("a transition must advance simulation time")
        if self._last_tick is not None and before.tick != self._last_tick:
            raise ValueError("transition is not contiguous with the previous transition")
        transition = canonical_json(
            {
                "observation": before,
                "command": command,
                "next_observation": after,
                "duration_s": after.time_s - before.time_s,
            }
        )
        evaluation = canonical_json(
            {"tick": after.tick, "diagnostics": diagnostics, "task": task_result}
        )
        self._transitions.write(transition + "\n")
        self._evaluation.write(evaluation + "\n")
        self._transitions.flush()
        self._evaluation.flush()
        self._last_tick = after.tick

    def close(self, status: str, reason: str) -> None:
        if self._closed:
            return
        if status not in {"completed", "failed", "interrupted"}:
            raise ValueError("invalid episode status")
        self._transitions.close()
        self._evaluation.close()
        (self.directory / "outcome.json").write_text(
            canonical_json({"status": status, "reason": reason, "last_tick": self._last_tick})
            + "\n",
            encoding="utf-8",
        )
        self._closed = True


def read_transitions(directory: Path) -> list[dict[str, Any]]:
    with (directory / "transitions.jsonl").open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]
