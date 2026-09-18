# Public-data admission audit

Status: reconstruction and exploratory comparison only. No physical-validation pass.

## Robotic rheometer

Pinned source: [Ruck dataset, f4b98b7](https://github.com/johnruck-sed/GRL_2023_RobotRheometer/tree/f4b98b71162ab4400fb3ad3bedb38a4b71a3a8b1).
The downloaded repository inventory has no explicit license. Raw data is retained
locally and is not redistributed in this repository. The fetcher and checksum
manifest allow independent retrieval.

`lab_data/VolumeFracTrials.csv` contains 1,861 rows for each of two packing
conditions, 0.57 and 0.59. The source notebook defines columns 0/1 and 3/4 as
depth/force, an area of 0.00016129 m², radius 0.00635 m, solid density 2,500 kg/m³,
and gravity 9.8 m/s². It negates the force and subtracts 1.5 radii from depth.
Our loader reproduces these operations without executing the notebook, filtering
samples, or fitting an outcome-dependent registration.

The [paper's apparatus description](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023GL106468)
specifies a 1.27 cm square rod, 1 cm/s downward motion, and a cylindrical sand bed.
Force is inferred from motor torque, not directly measured with a load cell.
The two condition curves do not expose a clear independent-repeat grouping or
measurement uncertainty. Recorded depth extends beyond the described penetration
range, so the full series must not be treated as a monotonic prescribed intrusion.

**Admission:** suitable for reproducing the published nondimensional curves and
planning a force fixture; insufficient for the proposed independent physical
acceptance test until trial segmentation, repeatability, and apparatus assumptions
are resolved. The current large-box fixture is not a geometric match.

## DDBot sand

Pinned source: [DDBot, e642f7c](https://github.com/IanYangChina/DDBot-IEEE-TRO-2025/tree/e642f7c73f37539c21161bd29669fa8d91912b88),
which includes an MIT license. Downloaded assets include both sand surface targets,
two motion sequences, experiment construction code, and the referenced shovel mesh.
Git LFS assets are downloaded as content and checked against their pointer hashes.
No upstream Python, notebook, pickle, or model checkpoint is executed.

The [paper](https://arxiv.org/html/2510.17335v2) distinguishes a system-identification
motion and a separate validation motion. Our initial split follows that distinction:
trial 0 is development; trial 1 is reserved for evaluation after freezing the model.
Metadata inspection of trial 1 has occurred; it has not been used to fit parameters.

Important reconstruction details verified from source:

- `sys_id_sim_*_pos-dt_0.01.npy` contains six-component **increments**, not absolute
  poses. Position control divides each increment across substeps.
- `make_env` selects `shovel_eef.yaml`, which references `ShovelEEF.obj`; the similarly
  named `new_shovel_eef.yaml` is not the system-identification tool configuration.
- The bed spans (0.06, 0.06, 0.015) to (0.34, 0.34, 0.085) m. Its uniform initial
  state comes from the authors' reconstruction, not a measured initial scan.
- Initial tool position is (0.2, 0.2, 0.205) m, with the documented Euler transform.
- Surface comparison uses a 0.24 m square centered at (0.2, 0.2), at 40 x 40 pixels.
  The first array axis is x. Surface heights include the bed's 0.015 m offset.
- Motion is planned by MoveIt. Tracking error is not measured in the downloaded
  motion arrays. Final surface evidence does not establish transient force accuracy.

**Admission:** suitable with stated uncertainty for exploratory conditional terrain
replay. Independent physical acceptance still needs a stated useful tolerance,
numerical stability/convergence, calibration on development data only, and assessed
uncertainty from initial preparation, motion tracking, walls, and surface processing.
Executing one uncalibrated comparison does not satisfy those gates.

The replay uses physical side walls instead of the upstream numerical boundary and
does not impose the upstream top clipping plane. This choice is recorded explicitly
and must be assessed as a model difference before claiming reproduction of its simulator.
