# Public validation target selection

The user has no machine/site access and has authorized selecting suitable public
data. Personal access to a machine is no longer a prerequisite for choosing the
target. Discovery does not establish data admission or physical accuracy.

## Decision

Prioritize **UIUC UR5e scooping** for the first soil-interaction benchmark.
Investigate **RWTH Volvo EW160D trench excavation/backfilling** as the full-size
machine target. Keep their claims separate: a laboratory scoop cannot qualify a
construction excavator, and pressure logs alone cannot validate soil deformation.
The existing numerical failures remain open.

## UIUC: first component target

[Author project](https://drillaway.github.io/scooping-dataset.html) and
[dataset](https://huggingface.co/datasets/pthangeda/scooping-dataset).
The release describes 6,700 scoops across 67 terrains, pre-action RGB-D, force/torque
records, action parameters and measured scoop volume. The dataset card declares
CC BY 4.0. Begin with a documented single-material sand subset; other materials
must not inherit a sand-model validity claim.

The [paper](https://arxiv.org/html/2303.02893v2) documents an impedance-controlled
UR5e scoop, approximate tray dimensions, trajectory parameters and stiffnesses.
Volume is inferred from depth measurements in a fixed scoop pose, not independent
weighing. Commanded trajectory parameters are not measured tool motion.

Verified retrieval: pinned Hugging Face revision
`74f8f8ac59a78a3f3710885b56fdaf119e7605ce`. Before reading measurements,
`terrain_1_sample_1` was designated schema-development only. Its force CSV is
downloadable and has 733 rows and six columns, without a timestamp column or
header. Remaining numerical trial outcomes were not inspected. This record is not
a qualification holdout. The original terrain table subsequently confirmed terrain
1 as single-material sand; equivalence of the converted measurements to the original
arrays remains to be checked.

Admission work: verify trial/material mapping, reconcile the converted release
with the original, establish force order/units/frame/rate/tare, obtain scoop
geometry and camera calibration, and resolve motion tracking and volume uncertainty.
Freeze splits and useful accuracy criteria before qualification evaluation.

### Original documentation and inventory audit

The public Box folder was accessible through the browser without a login. Its
[original README](https://uofi.app.box.com/s/vid2ycxzgqrzdn2w2vr0xkxwwjzpj5p8/file/1238032743312)
confirms image shape `(720, 1280, 4)`, action/outcome shape `(100, 6)`, and field
order `[pixel_x, pixel_y, yaw, scoop_depth, stiffness, scooped_volume]`. It assigns
radians to yaw, meters to depth, cubic meters to volume, and binary low/high
stiffness values. It does not supply force sampling rate, force channel mapping,
sensor frame, calibration, or measured tool trajectories.

The [original terrain table](https://uofi.app.box.com/s/vid2ycxzgqrzdn2w2vr0xkxwwjzpj5p8/file/1238050100136)
identifies terrain 1 as single sand, terrain 2 as single pebbles, terrain 3 as
single slate, and terrain 4 as single gravel. This was read from the browser
preview; no original-array equality check is implied. The original archive is
listed as 38.1 GB and was not downloaded.

The pinned Hugging Face file inventory contains exactly 6,700 RGB paths, 6,700
depth paths and 6,700 force paths, each covering terrain IDs 1–67 and sample IDs
1–100 once. No missing, extra or duplicate trial identifiers were found in those
three channels. This checks listed names only, not remote content integrity,
independence of trials or measurement accuracy. The audit and source-response
hash are retained in `docs/evidence/public-selection/scooping-inventory.json`.

## RWTH: full-size machine candidate

[University record](https://publications.rwth-aachen.de/record/1037760),
DOI `10.18154/RWTH-2026-06233`, describes a Volvo EW160D trenching/backfilling
recording with hydraulic pressure, temperature, cylinder/link sensors and CAN data.
The record displays CC BY 4.0 and links a README and pickle file.

The raw README request returned an HTML browser challenge rather than documentation;
that response is not admitted as a README. No pickle was loaded. File accessibility,
channel calibration, machine/linkage/bucket geometry, soil characterization and
terrain/mass observations remain unverified. Pressure must not be relabeled bucket
force without the mechanical and hydraulic reconstruction.
The browser attempt also remained on a loading screen and did not expose README
content; raw-file access remains unresolved.

## Supplementary option

[Fuxi excavator-motion](https://huggingface.co/datasets/fuxi-robot/excavator-motion)
documents timestamped joint angles, RGB and elevation images for three machine
models, with a CC BY-NC-SA 4.0 license. Its described schema does not include
reaction forces. The next joint-angle sample is labeled action; it must not be
treated as an actuator command. Revision identified:
`7eb0cd4011eb8b7ecbbaa4deac53378192901fad`. This is a motion/perception candidate,
not a replacement for force validation; metric elevation decoding needs checking.

## Retained evidence

Local metadata, pinned README, one development CSV and its SHA-256 manifest are
under `data/raw/admission/public-selection/`. A portable retrieval manifest is in
`docs/evidence/public-selection/`. No full dataset download, model fit, held-out
evaluation or physical-validation pass is claimed by this selection.
