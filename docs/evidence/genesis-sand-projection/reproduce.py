"""Audit the retained installed-material probe and its elastic counterfactual."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np

folder = Path(__file__).resolve().parent
manifest = json.loads((folder / "manifest.json").read_text())
for name, digest in manifest["files"].items():
    assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
records = [json.loads((folder / f"projection{bits}.json").read_text()) for bits in (32, 64)]
assert records[0]["source_sha256"] == records[1]["source_sha256"]
assert records[0]["input_log_strain"] == records[1]["input_log_strain"]
strain = np.asarray(records[0]["input_log_strain"])
deviator = strain - strain.mean()
mu = 1e6 / (2 * 1.3)
lam = 1e6 * 0.3 / (1.3 * 0.4)
sin_phi = math.sin(math.atan(0.6))
alpha = math.sqrt(2 / 3) * 2 * sin_phi / (3 - sin_phi)
yield_term = (3 * lam + 2 * mu) / (2 * mu) * strain.sum() * alpha
base_gamma = np.linalg.norm(deviator) + yield_term
assert base_gamma < 0
errors = []
for record in records:
    eps = record["effective_epsilon"]
    gamma = math.sqrt(float(deviator @ deviator) + eps) + yield_term
    np.testing.assert_allclose(gamma, record["regularized_delta_gamma"], rtol=1e-12)
    np.testing.assert_allclose(base_gamma, record["unregularized_delta_gamma"], rtol=1e-12)
    errors.append(float(np.max(np.abs(np.asarray(record["installed_projected_log_strain"])
                                     - strain))))
assert records[0]["regularized_delta_gamma"] > 0
assert records[1]["regularized_delta_gamma"] < 0
assert errors[0] > 1e-7 and errors[1] < 1e-14
print(json.dumps(dict(evidence_integrity=True, physical_validation=False,
                      max_log_strain_change_32=errors[0], max_log_strain_change_64=errors[1],
                      interpretation=("The regularizer changes the yield decision for this probe; "
                                      "its contribution to digging drift remains unproven")),
                 indent=2))
