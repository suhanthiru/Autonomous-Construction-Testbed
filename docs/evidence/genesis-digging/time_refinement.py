"""Recompute the digging timestep comparison or hard-contact control."""

import argparse
import gzip
import json
from pathlib import Path

from reproduce import audit

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
variants = parser.add_mutually_exclusive_group()
variants.add_argument("--hard-contact", action="store_true")
variants.add_argument("--double-precision", action="store_true")
args = parser.parse_args()
names = ["genesis-digging", "genesis-digging-dt200us", "genesis-digging-dt100us"]
if args.hard_contact:
    names = ["genesis-digging-hard-dt400us", "genesis-digging-hard-dt200us"]
if args.double_precision:
    names = ["genesis-digging-f64-dt400us", "genesis-digging-f64-dt200us"]
audits = [audit(root / name) for name in names]
records = [json.loads(gzip.decompress((root / name / "record.json.gz").read_bytes()))
           for name in names]
fixed = ("voxel_m", "spacing_m", "backend", "material", "world_offset_m",
         "coupling_softness_m", "coupling_friction", "domain_lower_m", "domain_upper_m",
         "mass_scale", "particle_count", "physical_mass_kg", "initial_momentum_kg_m_s",
         "script_sha256", "source_commit", "packages")
if args.double_precision:
    fixed += ("precision", "effective_epsilon")
    assert all(r["precision"] == "64" for r in records)
for record in records[1:]:
    for key in fixed:
        if record[key] != records[0][key]:
            raise ValueError(f"Uncontrolled recorded input: {key}")
assert [r["dt_s"] for r in records] == ([0.0004, 0.0002] if len(records) == 2
                                       else [0.0004, 0.0002, 0.0001])
changes = []
for a, b in zip(audits[:-1], audits[1:], strict=True):
    changes.append({key: b[key] / a[key] - 1 for key in
                    ("tool_vertical_impulse_n_s", "peak_20ms_mean_n")})
print(json.dumps(dict(audits=audits, timestep_s=[r["dt_s"] for r in records],
                      relative_changes=changes, recorded_fixed_inputs_match=True,
                      physical_validation=False,
                      interpretation="Reports sensitivity; no physical gate is evaluated"),
                 indent=2, allow_nan=False))
