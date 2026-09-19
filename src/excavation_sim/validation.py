"""Fail-closed coverage reporting. Evidence review is distinct from test execution."""

import json
from pathlib import Path

from excavation_sim.provenance import fingerprint

REQUIRED_GATES = frozenset(
    {
        "software_contracts",
        "rigid_momentum",
        "soil_momentum",
        "contact_convergence",
        "terrain_convergence",
        "force_data_admission",
        "terrain_data_admission",
        "physical_force",
        "physical_terrain",
        "repeated_excavation",
        "machine_actuation",
    }
)


def validation_snapshot(root: Path) -> dict:
    """Capture assessments at run time; never infer a validated operating envelope."""
    path = root / "validation" / "coverage.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        status = coverage_status(root, manifest)
        return {
            **status,
            "manifest_canonical_sha256": fingerprint(manifest),
            "scope": manifest.get("scope"),
            "applicability": "Recorded gate status only; no automatic claim that this "
            "experiment lies within a validated physical operating envelope.",
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {
            "validation_complete": False,
            "unresolved": sorted(REQUIRED_GATES),
            "errors": [f"validation manifest unavailable or malformed: {type(error).__name__}"],
            "manifest_canonical_sha256": None,
            "gates": [],
        }


def require_passed_gates(snapshot: dict) -> None:
    if not snapshot.get("validation_complete") or snapshot.get("errors"):
        raise ValueError(
            "Recorded validation gates have not passed: "
            + ", ".join(snapshot.get("unresolved", []))
            + ("; " + "; ".join(snapshot["errors"]) if snapshot.get("errors") else "")
        )


def coverage_status(root: Path, manifest: dict) -> dict:
    gates = manifest.get("gates", [])
    ids = [gate["id"] for gate in gates]
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate gate ids")
    missing = sorted(REQUIRED_GATES - set(ids))
    if missing:
        errors.append(f"missing required gates: {', '.join(missing)}")
    for gate in gates:
        if gate.get("status") not in {"passed", "failed", "not_assessed"}:
            errors.append(f"invalid status: {gate['id']}")
        if gate.get("status") == "passed":
            evidence = gate.get("evidence")
            if not evidence:
                errors.append(f"passing gate has no pinned evidence: {gate['id']}")
                continue
            try:
                path = (root / evidence["path"]).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file():
                    errors.append(f"missing or external evidence: {gate['id']}")
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                if fingerprint(data) != evidence.get("canonical_json_sha256"):
                    errors.append(f"evidence checksum mismatch: {gate['id']}")
            except (OSError, ValueError, TypeError, KeyError):
                errors.append(f"unreadable or malformed evidence: {gate['id']}")
    unresolved = [g["id"] for g in gates if g.get("status") != "passed"]
    complete = not errors and not unresolved and REQUIRED_GATES.issubset(ids)
    return {
        "validation_complete": complete,
        "unresolved": unresolved,
        "errors": errors,
        "gates": gates,
        "note": "Checks recorded assessments and evidence integrity; does not rerun physics.",
    }
