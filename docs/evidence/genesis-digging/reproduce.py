"""Audit retained numerical traces without interpreting them as physical validation."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np


def audit(folder):
    summary = json.loads((folder / "summary.json").read_text())
    raw = gzip.decompress((folder / "record.json.gz").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == summary["record_sha256"]
    record = json.loads(raw)
    assert not record["script_changed"] and not record["physical_validation"]
    source = (folder / "run-source.py.txt").read_bytes()
    assert hashlib.sha256(source).hexdigest() == record["script_sha256"]
    dt = record["dt_s"]
    rows = record["trajectory"]
    assert len(rows) == round(1.2 / dt)
    previous = np.asarray(record["initial_momentum_kg_m_s"])
    impulses, residuals = [], []
    offset = record["world_offset_m"][2]
    max_position_error = max_velocity_error = max_orientation_error = 0.0
    for tick, row in enumerate(rows):
        t = tick * dt
        assert abs(row["time_s"] - (tick + 1) * dt) < 1e-12
        expected = [offset, offset, 0.35 + offset - 0.3 * min(t, 0.8)
                    + 0.3 * max(t - 0.8, 0)]
        velocity = [0, 0, -0.3 if tick < round(0.8 / dt) else 0.3]
        np.testing.assert_allclose(row["command_position_m"], expected, rtol=0, atol=1e-14)
        np.testing.assert_allclose(row["command_velocity_m_s"], velocity, rtol=0, atol=0)
        pos_error = np.max(np.abs(np.asarray(row["collider_position_m"]) - expected))
        vel_error = np.max(np.abs(np.asarray(row["collider_velocity_m_s"]) - velocity))
        quat = np.asarray(row["collider_quaternion_wxyz"])
        quat_error = min(np.linalg.norm(quat - [1, 0, 0, 0]),
                         np.linalg.norm(quat + [1, 0, 0, 0]))
        assert max(pos_error, vel_error, quat_error) <= 1e-7
        max_position_error = max(max_position_error, float(pos_error))
        max_velocity_error = max(max_velocity_error, float(vel_error))
        max_orientation_error = max(max_orientation_error, float(quat_error))
        gravity = np.asarray([0, 0, -9.81]) * record["physical_mass_kg"] * dt
        np.testing.assert_allclose(row["gravity_impulse_n_s"], gravity, rtol=0, atol=1e-14)
        momentum = np.asarray(row["momentum_kg_m_s"])
        reaction = np.asarray(row["all_reaction_impulse_n_s"])
        residual = momentum - previous - gravity + reaction
        np.testing.assert_allclose(row["unaccounted_momentum_n_s"], residual,
                                   rtol=0, atol=1e-14)
        assert np.isfinite(residual).all()
        lo = np.asarray(row["position_min_m"])
        hi = np.asarray(row["position_max_m"])
        assert np.isfinite(lo).all() and np.isfinite(hi).all() and np.all(lo <= hi)
        assert np.all(lo >= np.asarray(record["domain_lower_m"]) + 3 * record["voxel_m"])
        assert np.all(hi <= np.asarray(record["domain_upper_m"]) - 3 * record["voxel_m"])
        impulses.append(row["tool_reaction_impulse_n_s"][2])
        residuals.append(residual)
        previous = momentum
    window = round(0.02 / dt)
    assert len(rows) % window == 0
    means = np.asarray(impulses).reshape(-1, window).sum(axis=1) / 0.02
    np.testing.assert_allclose(sum(impulses), record["tool_vertical_impulse_n_s"], rtol=1e-12)
    np.testing.assert_allclose(max(means), record["peak_20ms_mean_n"], rtol=1e-12)
    return dict(record_integrity=True, physical_validation=False, steps=len(rows),
                tool_vertical_impulse_n_s=sum(impulses), peak_20ms_mean_n=float(max(means)),
                cumulative_unaccounted_momentum_n_s=np.sum(residuals, axis=0).tolist(),
                max_step_unaccounted_momentum_n_s=np.max(np.abs(residuals), axis=0).tolist(),
                max_position_error_m=max_position_error,
                max_velocity_error_m_s=max_velocity_error,
                max_orientation_quaternion_error=max_orientation_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=Path(__file__).parent)
    print(json.dumps(audit(parser.parse_args().folder), indent=2, allow_nan=False))
