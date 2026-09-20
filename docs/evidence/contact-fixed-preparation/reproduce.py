"""Audit preparation and digging records separately from retained raw data."""

import gzip
import importlib.util
import json
import math
import re
from pathlib import Path


def audit_record(folder, summary):
    spec = importlib.util.spec_from_file_location(
        "contact_audit", folder.parent / "contact-spatial-refinement/reproduce.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    digging = audit.audit(folder, summary)
    data = json.loads(gzip.decompress((folder / summary["file"]).read_bytes()))
    prep = data["preparation"]
    trace = prep["trajectory"]
    audit.require(len(trace) > 0, "Missing preparation")
    audit.require(math.isclose(len(trace) * prep["dt_s"], prep["duration_s"]),
                  "Incomplete preparation duration")
    failed = 0
    for index, row in enumerate(trace):
        audit.require(math.isclose(row["time_s"], (index + 1) * prep["dt_s"]),
                      "Irregular preparation timestamps")
        matches = re.findall(r"terminated after (\d+) iterations with residuals ([^,\s]+), "
                             r"([^\s]+)", row["solver_diagnostic"])
        audit.require(len(matches) == 1, "Missing or ambiguous preparation residuals")
        values = [float(v) for v in matches[0][1:]]
        failed += not all(math.isfinite(v) and v <= data["mpm"]["tolerance"] for v in values)
        speeds = [row[k] for k in ("rms_particle_speed_m_s", "max_particle_speed_m_s")]
        audit.require(all(math.isfinite(v) for v in speeds) and 0 <= speeds[0] <= speeds[1],
                      "Invalid preparation speeds")
    tail = [r for r in trace if r["time_s"] > prep["duration_s"] - 0.1]
    return dict(digging=digging, preparation_steps=len(trace),
                          preparation_dt_s=prep["dt_s"],
                          preparation_duration_s=prep["duration_s"],
                          state_fingerprints=prep.get("state_fingerprints", {}),
                          preparation_failed_steps=failed,
                          preparation_inner_passed=failed == 0,
                          final_max_speed_m_s=trace[-1]["max_particle_speed_m_s"],
                          final_rms_speed_m_s=trace[-1]["rms_particle_speed_m_s"],
                          last_100ms_max_speed_m_s=max(r["max_particle_speed_m_s"] for r in tail),
                          evidence_integrity_passed=True, equilibrium_qualified=False,
                          physical_validation=False)


def main():
    folder = Path(__file__).resolve().parent
    summary = json.loads((folder / "q1-settle1-summary.json").read_text())
    print(json.dumps(audit_record(folder, summary), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
