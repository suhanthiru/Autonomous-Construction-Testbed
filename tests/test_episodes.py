import json

import pytest
from test_rollout import FixtureWorld, Policy

from excavation_sim.episodes import load_episode
from excavation_sim.rollout import rollout


def test_typed_roundtrip_excludes_privileged_stream_and_detects_tampering(tmp_path):
    directory = tmp_path / "episode"
    rollout(FixtureWorld(), Policy(), directory, seed=0, actions=3, config={}, source_root=tmp_path)
    (directory / "evaluation.jsonl").write_text("unreadable privileged data")
    result = load_episode(directory)
    assert len(result) == 3
    assert result[-1].next_observation.tick == 6
    path = directory / "transitions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1]["observation"]["tool_position_m"][0] = 100
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="discontinuous"):
        load_episode(directory)
