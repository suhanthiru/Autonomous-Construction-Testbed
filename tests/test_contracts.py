import json

import pytest

from excavation_sim.core import (
    BackendInfo,
    Capability,
    Clock,
    Diagnostics,
    Observation,
    ToolCommand,
)
from excavation_sim.provenance import canonical_json, fingerprint, source_identity
from excavation_sim.recording import EpisodeWriter, read_transitions


def observation(tick):
    return Observation(tick, tick * 0.01, (0, 0, 0), (0, 0, 0), (0, 0, 0))


def test_capabilities_reject_unsupported_physics():
    backend = BackendInfo("fixture", "1", frozenset({Capability.MOTION_REPLAY}), ())
    with pytest.raises(ValueError, match="granular_soil"):
        backend.require(frozenset({Capability.GRANULAR_SOIL}))


@pytest.mark.parametrize("dt,steps", [(0, 1), (float("nan"), 1), (0.01, 0), (0.01, True)])
def test_clock_rejects_invalid_settings(dt, steps):
    with pytest.raises(ValueError):
        Clock(dt, steps)


def test_tick_time_does_not_accumulate_float_error():
    assert Clock(0.001, 10).time_s(1_000_000) == 1000


def test_invalid_command_fails_before_physics():
    with pytest.raises(ValueError):
        ToolCommand((0, float("inf"), 0))


def test_recording_separates_privileged_state_and_rejects_gaps(tmp_path):
    path = tmp_path / "episode"
    writer = EpisodeWriter(path, {"schema_version": 1})
    command = ToolCommand((0, 0, -0.1))
    diagnostics = Diagnostics(2.5, 0, True, (0, 0, 1))
    writer.append(observation(0), command, observation(10), diagnostics)
    with pytest.raises(ValueError, match="contiguous"):
        writer.append(observation(20), command, observation(30), diagnostics)
    writer.close("completed", "time_limit")
    transitions = read_transitions(path)
    assert len(transitions) == 1
    assert "particle_mass_kg" not in json.dumps(transitions)
    assert (
        json.loads((path / "evaluation.jsonl").read_text())["diagnostics"]["particle_mass_kg"]
        == 2.5
    )
    assert json.loads((path / "outcome.json").read_text())["last_tick"] == 10
    with pytest.raises(FileExistsError):
        EpisodeWriter(path, {})


def test_nan_cannot_be_silently_recorded():
    with pytest.raises(ValueError):
        canonical_json({"force": float("nan")})


def test_config_hash_is_independent_of_mapping_order():
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_source_identity_includes_untracked_code(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    file = source / "new.py"
    file.write_text("x = 1\n")
    before = source_identity(tmp_path)["source_sha256"]
    file.write_text("x = 2\n")
    assert before != source_identity(tmp_path)["source_sha256"]


def test_generated_package_metadata_is_not_source(tmp_path):
    from excavation_sim.provenance import source_identity

    generated = tmp_path / "src" / "example.egg-info"
    generated.mkdir(parents=True)
    metadata = generated / "PKG-INFO"
    metadata.write_text("first build")
    first = source_identity(tmp_path)["source_sha256"]
    metadata.write_text("second build")
    assert source_identity(tmp_path)["source_sha256"] == first
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_behavior.py").write_text("assert True")
    assert source_identity(tmp_path)["source_sha256"] != first
