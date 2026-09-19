import json

import pytest

from excavation_sim.provenance import fingerprint
from excavation_sim.validation import (
    REQUIRED_GATES,
    coverage_status,
    require_passed_gates,
    validation_snapshot,
)


def test_empty_or_partial_validation_cannot_pass(tmp_path):
    assert not coverage_status(tmp_path, {"gates": []})["validation_complete"]
    result = coverage_status(
        tmp_path, {"gates": [{"id": "software_contracts", "status": "passed"}]}
    )
    assert not result["validation_complete"]
    assert result["errors"]


def test_passes_without_evidence_cannot_complete_validation(tmp_path):
    result = coverage_status(
        tmp_path, {"gates": [{"id": g, "status": "passed"} for g in REQUIRED_GATES]}
    )
    assert not result["validation_complete"]


def test_failed_gate_is_reported(tmp_path):
    gates = [{"id": g, "status": "not_assessed"} for g in REQUIRED_GATES]
    gates[0]["status"] = "failed"
    result = coverage_status(tmp_path, {"gates": gates})
    assert len(result["unresolved"]) == len(REQUIRED_GATES)
    assert not result["validation_complete"]


def test_evidence_tampering_invalidates_recorded_pass(tmp_path):
    data = {"assessment": "passed", "scope": "synthetic reporting test"}
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(data))
    gates = [
        {
            "id": g,
            "status": "passed",
            "evidence": {"path": "evidence.json", "canonical_json_sha256": fingerprint(data)},
        }
        for g in REQUIRED_GATES
    ]
    assert coverage_status(tmp_path, {"gates": gates})["validation_complete"]
    evidence.write_text(json.dumps({"assessment": "changed"}))
    result = coverage_status(tmp_path, {"gates": gates})
    assert not result["validation_complete"]
    assert any("checksum mismatch" in error for error in result["errors"])
    evidence.write_text("not JSON")
    result = coverage_status(tmp_path, {"gates": gates})
    assert not result["validation_complete"]
    assert any("malformed" in error for error in result["errors"])


def test_missing_or_malformed_snapshot_cannot_authorize_a_run(tmp_path):
    with pytest.raises(ValueError, match="have not passed"):
        require_passed_gates(validation_snapshot(tmp_path))
    folder = tmp_path / "validation"
    folder.mkdir()
    (folder / "coverage.json").write_text('{"gates":null}')
    with pytest.raises(ValueError, match="malformed"):
        require_passed_gates(validation_snapshot(tmp_path))


def test_snapshot_preserves_failed_assessment_and_its_identity(tmp_path):
    folder = tmp_path / "validation"
    folder.mkdir()
    manifest = {
        "scope": "fixture",
        "gates": [
            {"id": name, "status": "failed", "reason": "measured discrepancy"}
            for name in REQUIRED_GATES
        ],
    }
    path = folder / "coverage.json"
    path.write_text(json.dumps(manifest))
    snapshot = validation_snapshot(tmp_path)
    assert snapshot["manifest_canonical_sha256"] == fingerprint(manifest)
    path.write_text('{"gates": []}')
    assert snapshot["gates"] == manifest["gates"]
    with pytest.raises(ValueError, match="have not passed"):
        require_passed_gates(snapshot)
