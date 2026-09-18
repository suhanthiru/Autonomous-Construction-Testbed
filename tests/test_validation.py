import json

from excavation_sim.provenance import fingerprint
from excavation_sim.validation import REQUIRED_GATES, coverage_status


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
