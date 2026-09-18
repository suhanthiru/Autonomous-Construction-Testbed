# Third-party notices

The coupling fixture in `scripts/check_soil_coupling.py` adapts the solver setup from
Newton 1.6.0's `example_mujoco_mpm_coupled_solver.py` (Copyright 2026 The Newton
Developers), licensed under Apache-2.0. Its license is included in
`licenses/Apache-2.0.txt`.

Changes include using XPBD, a smaller centered particle grid, a single box, an
empty-bed control, explicit finite-state checks, and JSON provenance recording.
Newton and Warp are installed dependencies; their distributions retain their own notices.

The DDBot replay reconstructs the experiment configuration and surface measurement
conventions from Xintong Yang's DDBot repository, revision
`e642f7c73f37539c21161bd29669fa8d91912b88`. Its MIT license is preserved in
`licenses/DDBot-MIT.txt`. Source meshes, planned trajectories, and measured targets
are downloaded into ignored data directories. Derived terrain figures identify the
source in the validation documentation. See `docs/DATA_ADMISSION.md` for the paper
and exact source links. The independent Newton implementation does not execute the
upstream simulator or load its pickled assets.
