import pytest
from test_rollout import FixtureWorld, Policy

from excavation_sim.packed import export_episode, iter_records
from excavation_sim.recording import read_transitions
from excavation_sim.rollout import rollout


def test_chunked_round_trip_and_checksum_rejects_corruption(tmp_path):
    source, target = tmp_path / "episode", tmp_path / "packed"
    rollout(FixtureWorld(), Policy(), source, seed=0, actions=5, config={}, source_root=tmp_path)
    index = export_episode(source, target, chunk_size=2)
    assert len(index["shards"]) == 3
    assert list(iter_records(target)) == read_transitions(source)
    path = target / index["shards"][0]["file"]
    path.write_bytes(path.read_bytes() + b"corruption")
    with pytest.raises(ValueError, match="checksum"):
        list(iter_records(target))
