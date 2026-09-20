"""Recompute accounting metrics without asserting a physical validation pass."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path


def main(folder=None, case=None):
    folder = Path(folder).resolve() if folder else Path(__file__).resolve().parent
    results = []
    fixed_inputs = None
    seen = set()
    for summary in json.loads((folder / "summaries.json").read_text()):
        if case is not None and summary["case"] != case:
            continue
        raw = gzip.decompress((folder / summary["file"]).read_bytes())
        if hashlib.sha256(raw).hexdigest() != summary["canonical_json_sha256"]:
            raise ValueError("Raw evidence checksum differs")
        data = json.loads(raw)
        if data["case"] in seen:
            raise ValueError("Duplicate case")
        seen.add(data["case"])
        fixed = {k: data[k] for k in ("backend", "dt_s", "steps", "particle_count",
                                      "physical_mass_kg", "mass_scale", "script_sha256",
                                      "initial_momentum_kg_m_s")}
        if fixed_inputs is not None and fixed != fixed_inputs:
            raise ValueError("Uncontrolled configuration or initial momentum difference")
        fixed_inputs = fixed
        rows = data["trajectory"]
        if data["case"] != summary["case"] or len(rows) != data["steps"]:
            raise ValueError("Case identity or step count differs")
        previous = data["initial_momentum_kg_m_s"]
        reaction, residual = [0.0] * 3, [0.0] * 3
        max_residual = max_reaction = 0.0
        for index, row in enumerate(rows):
            if not math.isclose(row["time_s"], (index + 1) * data["dt_s"]):
                raise ValueError("Incomplete or irregular trace")
            for key in ("momentum_kg_m_s", "reaction_impulse_n_s", "unaccounted_momentum_n_s"):
                if len(row[key]) != 3 or not all(math.isfinite(v) for v in row[key]):
                    raise ValueError(f"Invalid accounting vector: {key}")
            current = row["momentum_kg_m_s"]
            for axis in range(3):
                impulse = row["reaction_impulse_n_s"][axis]
                value = current[axis] - previous[axis] + impulse
                if not math.isclose(value, row["unaccounted_momentum_n_s"][axis],
                                    rel_tol=0, abs_tol=1e-14):
                    raise ValueError("Stored residual does not reproduce")
                reaction[axis] += impulse
                residual[axis] += value
                max_residual = max(max_residual, abs(value))
                max_reaction = max(max_reaction, abs(impulse))
            previous = current
        results.append(dict(case=data["case"], steps=len(rows),
                            physical_mass_kg=data["physical_mass_kg"],
                            cumulative_reaction_n_s=reaction,
                            cumulative_unaccounted_momentum_n_s=residual,
                            max_abs_step_residual_n_s=max_residual,
                            max_abs_step_reaction_n_s=max_reaction))
    if seen != ({case} if case else {"free", "contact"}):
        raise ValueError("Requested controls are missing")
    print(json.dumps(dict(cases=results, fixed_inputs=fixed_inputs, evidence_integrity_passed=True,
                          scope="single trace" if case else "paired controls",
                          physical_validation=False), indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path)
    parser.add_argument("--case", choices=("free", "contact"))
    args = parser.parse_args()
    main(args.folder, args.case)
