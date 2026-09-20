"""Audit recorded collider states at the prescribed coupling boundary."""

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path


def main(folder=None):
    folder = Path(folder).resolve() if folder else Path(__file__).resolve().parent
    study = json.loads((folder / "study.json").read_text())
    raw = gzip.decompress((folder / study["repeat_file"]).read_bytes())
    if hashlib.sha256(raw).hexdigest() != study["canonical_json_sha256"]:
        raise ValueError("Raw checksum differs")
    data = json.loads(raw)
    trace = data["trajectory"]
    if data["dt_s"] != 0.0001 or len(trace) != 400:
        raise ValueError("Wrong duration or timestep")
    maxima = {"position_m": 0.0, "velocity_m_s": 0.0}
    loaded = study.get("case") == "loaded"
    previous = data.get("initial_momentum_kg_m_s")
    reaction, residual_sum = [0.0] * 3, [0.0] * 3
    for index, row in enumerate(trace):
        t = index * data["dt_s"]
        expected_pos = [0.3 * min(t, 0.02) - 0.3 * max(t - 0.02, 0), 0, 0.2]
        expected_vel = [0.3 if index < 200 else -0.3, 0, 0]
        for command, observed, expected, metric, tolerance in (
            ("command_position_m", "collider_position_m", expected_pos, "position_m",
             study["boundary_position_tolerance_m"]),
            ("command_velocity_m_s", "collider_velocity_m_s", expected_vel, "velocity_m_s",
             study["boundary_velocity_tolerance_m_s"]),
        ):
            if len(row[command]) != 3 or len(row[observed]) != 3:
                raise ValueError("Invalid boundary vector")
            for cmd, actual, target in zip(row[command], row[observed], expected, strict=True):
                if not math.isclose(cmd, target, rel_tol=0, abs_tol=1e-14):
                    raise ValueError("Prescribed trajectory changed")
                error = abs(actual - target)
                if not math.isfinite(error) or error > tolerance:
                    raise ValueError("Collider boundary mismatch")
                maxima[metric] = max(maxima[metric], error)
        if row["collider_angular_velocity_rad_s"] != [0, 0, 0]:
            raise ValueError("Unexpected rotation")
        if not loaded and row["coupling_force_n"] != [[0, 0, 0]]:
            raise ValueError("Unexpected force in separated fixture")
        if loaded:
            if len(row["coupling_force_n"]) != 1 or len(row["coupling_force_n"][0]) != 3:
                raise ValueError("Unexpected force layout")
            current = row["momentum_kg_m_s"]
            for axis in range(3):
                impulse = row["coupling_force_n"][0][axis] * data["dt_s"]
                residual = current[axis] - previous[axis] + impulse
                if not (math.isfinite(impulse) and math.isfinite(residual)):
                    raise ValueError("Nonfinite accounting")
                if not math.isclose(impulse, row["reaction_impulse_n_s"][axis],
                                    rel_tol=0, abs_tol=1e-14):
                    raise ValueError("Impulse does not match recorded force")
                if not math.isclose(residual, row["unaccounted_momentum_n_s"][axis],
                                    rel_tol=0, abs_tol=1e-14):
                    raise ValueError("Momentum residual does not reproduce")
                reaction[axis] += impulse
                residual_sum[axis] += residual
            previous = current
    if loaded and not any(abs(v) > 0 for v in reaction):
        raise ValueError("Loaded control did not produce a net reaction")
    print(json.dumps(dict(steps=len(trace), maximum_errors=maxima,
                          cumulative_reaction_n_s=reaction if loaded else None,
                          cumulative_unaccounted_momentum_n_s=residual_sum if loaded else None,
                          boundary_checks_passed=True, physical_validation=False,
                          scope=study["scope"]), indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path)
    main(parser.parse_args().folder)
