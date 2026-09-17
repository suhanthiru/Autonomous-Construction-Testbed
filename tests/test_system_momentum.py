import json
import runpy
from pathlib import Path

import pytest


def test_system_ledger_exposes_temporary_momentum_gap(tmp_path):
    audit = runpy.run_path(str(Path(__file__).parents[1] / "scripts/audit_system_momentum.py"))[
        "audit"
    ]
    # Soil receives a downward unit impulse now; body receives the opposite one next step.
    rows = []
    for tick, velocity, generated, applied in [(1, 0, 1, 0), (2, 1, 0, 1)]:
        rows.append(
            {
                "tick": tick,
                "body_vz_m_s": velocity,
                "soil_momentum_kg_m_s": [0, 0, -1],
                "soil_impulse_n_s": [0, 0, generated],
                "impulse_on_ground_n_s": [0, 0, -0.0981],
                "actuator_force_z_n": 9.81,
                "applied_contact_impulse_z_n_s": applied,
            }
        )
    path = tmp_path / "record.json"
    path.write_text(
        json.dumps(
            {
                "dt_s": 0.01,
                "body_mass_kg": 1,
                "initial_soil_mass_kg": 1,
                "initial_soil_momentum_kg_m_s": [0, 0, 0],
                "trajectory": rows,
            }
        )
    )
    result = audit(path)
    assert result["soil_residual"]["max_abs_step_n_s"] == pytest.approx(0)
    assert result["system_residual"]["max_abs_step_n_s"] == pytest.approx(1)
    assert result["system_residual"]["signed_total_n_s"] == pytest.approx(0)
    assert result["system_residual_after_feedback_gap"]["max_abs_step_n_s"] == pytest.approx(0)
