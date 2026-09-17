# Third-party notices

The coupling fixture in `scripts/check_soil_coupling.py` adapts the solver setup from
Newton 1.6.0's `example_mujoco_mpm_coupled_solver.py` (Copyright 2026 The Newton
Developers), licensed under Apache-2.0. Its license is included in
`licenses/Apache-2.0.txt`.

Changes include using XPBD, a smaller centered particle grid, a single box, an
empty-bed control, explicit finite-state checks, and JSON provenance recording.
Newton and Warp are installed dependencies; their distributions retain their own notices.
