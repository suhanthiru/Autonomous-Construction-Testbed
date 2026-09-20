"""Audit recorded collider states at the prescribed coupling boundary."""

import gzip
import hashlib
import json
import math
from pathlib import Path


def main():
    folder = Path(__file__).resolve().parent
    study = json.loads((folder / "study.json").read_text())
    raw = gzip.decompress((folder / study["repeat_file"]).read_bytes())
    if hashlib.sha256(raw).hexdigest() != study["canonical_json_sha256"]:
        raise ValueError("Raw checksum differs")
    data = json.loads(raw)
    trace = data["trajectory"]
    if data["dt_s"] != 0.0001 or len(trace) != 400:
        raise ValueError("Wrong duration or timestep")
    maxima = {"position_m": 0.0, "velocity_m_s": 0.0}
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
        if row["coupling_force_n"] != [[0, 0, 0]]:
            raise ValueError("Unexpected force in separated fixture")
    print(json.dumps(dict(steps=len(trace), maximum_errors=maxima,
                          boundary_checks_passed=True, physical_validation=False,
                          scope=study["scope"]), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
