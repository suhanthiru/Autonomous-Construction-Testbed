"""Probe the installed sand return mapping near a compressive elastic state."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import genesis as gs
import numpy as np
import quadrants as qd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--precision", choices=("32", "64"), required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
gs.init(backend=gs.cpu, precision=args.precision, seed=0, logging_level="warning")
material = gs.materials.MPM.Sand(E=1e6, nu=0.3, friction_angle=math.degrees(math.atan(0.6)))
output = qd.Vector.field(3, dtype=gs.qd_float, shape=1)


@qd.kernel
def evaluate():
    strain = qd.Vector([-0.00011, -0.0001, -0.00009], dt=gs.qd_float)
    singular = qd.Matrix.zero(gs.qd_float, 3, 3)
    for i in qd.static(range(3)):
        singular[i, i] = qd.exp(strain[i])
    projected, _ = material._sand_projection(singular, gs.qd_float(0.0))
    for i in qd.static(range(3)):
        output[0][i] = qd.log(projected[i, i])


evaluate()
strain = np.array([-0.00011, -0.0001, -0.00009])
trace = strain.sum()
deviatoric_norm = float(np.linalg.norm(strain - trace / 3))
yield_term = (3 * material.lam + 2 * material.mu) / (2 * material.mu) * trace * material.alpha
nominal_delta_gamma = deviatoric_norm + yield_term
assert nominal_delta_gamma < 0, "Probe must be inside the unregularized elastic region"
paths = [Path(gs.__file__),
         Path(gs.__file__).parent / "engine/materials/MPM/sand.py",
         Path(qd.__file__).parent / "lang/matrix_ops.py"]
result = dict(precision=args.precision, effective_epsilon=gs.EPS,
              norm_floor=math.sqrt(gs.EPS), input_log_strain=strain.tolist(),
              unregularized_delta_gamma=nominal_delta_gamma,
              regularized_delta_gamma=math.sqrt(deviatoric_norm**2 + gs.EPS) + yield_term,
              installed_projected_log_strain=output.to_numpy()[0].tolist(),
              source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              physical_validation=False)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
print(json.dumps(result, indent=2))
