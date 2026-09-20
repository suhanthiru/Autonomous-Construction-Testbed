"""Audit the saved contact refinement evidence without importing the simulator."""

import gzip
import hashlib
import json
import math
import re
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(folder, record):
    path = folder / record["file"]
    data = json.loads(gzip.decompress(path.read_bytes()))
    canonical = json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    require(hashlib.sha256(canonical).hexdigest() == record["canonical_json_sha256"],
            f"Checksum mismatch: {path}")
    dt = data["dt_s"]
    trace = data["trajectory"]
    width = round(0.02 / dt)
    require(width > 0 and math.isclose(width * dt, 0.02), "Unaligned force window")
    require(len(trace) % width == 0, "Incomplete force window")
    require(math.isclose(len(trace) * dt, data["duration_s"]), "Incomplete trajectory")
    impulses = []
    outside = nonfinite = capped = 0
    for index, row in enumerate(trace):
        require(math.isclose(row["time_s"], (index + 1) * dt), "Irregular timestamps")
        require(all(math.isfinite(v) for v in row["impulse_n_s"]), "Nonfinite impulse")
        impulses.append(row["impulse_n_s"][2])
        matches = re.findall(
            r"terminated after (\d+) iterations with residuals ([^,\s]+), ([^\s]+)",
            row["solver_diagnostic"],
        )
        require(len(matches) == 1, "Missing or ambiguous solver residuals")
        iterations, first, second = matches[0]
        residuals = (float(first), float(second))
        finite = all(math.isfinite(v) for v in residuals)
        nonfinite += not finite
        outside += not finite or max(residuals) > data["mpm"]["tolerance"]
        capped += int(iterations) >= data["mpm"]["iterations"]
    force = [math.fsum(impulses[i:i + width]) / 0.02
             for i in range(0, len(impulses), width)]
    impulse = math.fsum(impulses)
    peak = max(force)
    reversal = round(0.8 / dt)
    require(math.isclose(reversal * dt, 0.8), "Unaligned motion reversal")
    loading = math.fsum(impulses[:reversal])
    withdrawal = math.fsum(impulses[reversal:])
    peak_bin = force.index(peak)
    require(math.isclose(impulse, data["total_vertical_impulse_n_s"], rel_tol=1e-12),
            "Stored impulse differs from trajectory")
    require(math.isclose(peak, data["peak_20ms_mean_n"], rel_tol=1e-12),
            "Stored peak differs from trajectory")
    health = dict(steps=len(trace), nonfinite_residual_steps=nonfinite,
                  outside_tolerance_steps=outside, at_iteration_limit_steps=capped,
                  passed=outside == 0)
    require(health == data["solver_health"], "Stored solver health differs from trace")
    require(not data["source_changed"], "Source changed during execution")
    require(data["mpm"]["sparse_capacity_checked_each_step"], "Capacity checks absent")
    return dict(file=record["file"], voxel_m=data["mpm"]["voxel_m"], dt_s=dt,
                impulse_n_s=impulse, peak_20ms_mean_n=peak, solver_health=health,
                loading_impulse_n_s=loading, withdrawal_impulse_n_s=withdrawal,
                peak_window_s=[peak_bin * 0.02, (peak_bin + 1) * 0.02],
                source_sha256=data["source"]["source_sha256"], physical_validation=False)


def main():
    folder = Path(__file__).resolve().parent
    coarse = folder.parent / "contact-grid-alignment"
    coarse_record = json.loads((coarse / "summary.json").read_text())["cases"][0]
    results = [audit(coarse, coarse_record)]
    for path in sorted(folder.glob("*-summary.json")):
        results.append(audit(folder, json.loads(path.read_text())))
    require(len({row["source_sha256"] for row in results}) == 1,
            "Refinement records use different source snapshots")
    print(json.dumps(dict(cases=results, evidence_integrity_passed=True,
                         physical_validation=False), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
