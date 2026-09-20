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

### Additional terrain reference under admission

The public [rigid-runner furrow dataset](https://zenodo.org/records/21159754)
is now the leading candidate for a **terrain-deformation component** reference.
Its pinned version declares CC BY 4.0 and includes raw/reconstructed scans,
tool STL files, and laboratory material measurements. The fine-sand archive
has been retrieved and matches the published MD5 checksum. Its inventory contains
150 raw OBJ trials and both tool meshes. Scan outcomes have not been opened.
The split reserves complete conditions: 25 plain-runner trials at the lowest
speed are development data; the other 125 are reserved pending admission and
accuracy preregistration. This prevents repeats of one condition crossing roles;
it does not establish independent preparation groups. No holdout is evaluated.
This candidate does not qualify a real excavator or replace the scooping task.

The [methods preprint](https://doi.org/10.21203/rs.3.rs-8287044/v1) describes
a 0.40 x 1.50 x 0.075 m bed, three speeds, five loads and repeated traverses.
Its detailed design explains the 375-versus-450 count: active-tool stone trials
were excluded after shocks/jamming/damage. Preserve this exclusion in any claim.
The speed table gives 0.051 m/s where one prose passage says 0.51 m/s;
resolve configuration mapping from records rather than silently merging them.

Admission still requires mesh units and orientation, load/guide boundary mapping,
preparation and scan registration, and an output-specific uncertainty model.
The laboratory PDF contains density values labelled kg/m3 in its summary but
g/cm3 in detailed tables. Its repose summary also needs reconciliation with
the underlying readings. Do not import either summary as unquestioned SI input.
The downloaded README refers to the older version DOI; use record 21159754 and
its checksums as the actual retrieval identity. No material fitting has begun.

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

### Example-code review and admission limits

The [original training example](https://uofi.app.box.com/s/vid2ycxzgqrzdn2w2vr0xkxwwjzpj5p8/file/1238046116258)
was inspected in the public browser preview on 2026-09-20, without executing it.
Its loop selects action row `i - 1` but constructs the image filename using the
literal `1`, so it reuses the first image for every trial. An importer must join
images, actions and force records by explicit terrain/sample identity. Do not
copy this loader as an authoritative preprocessing implementation. This finding
does not establish that the published experiments or converted release used it.
The example does not load force records or resolve their timing/calibration.

The [extended paper](https://arxiv.org/html/2408.02949v1) confirms the UIUC setup
and command parameters, but the inspected setup section does not establish the
missing force acquisition metadata or measured tracking. It also says actions
whose motion planning fails are discarded before execution; the dataset cannot
estimate planning-failure frequency from its successful records alone.

Current admission is **schema development only**. Before physical fitting:

1. Verify original-to-converted equality for the designated development sample;
   preserve original depth precision and trial identities.
2. Recover geometry, camera transforms and measurement definitions needed for
   the specific output. Unknown force timing blocks impulse/phase comparison;
   unknown channel units/frame blocks dimensional force comparison.
3. Establish preparation/reset groups before freezing a holdout. If those groups
   cannot be recovered, report that limitation rather than claiming independent
   trials from different timestamps or sample numbers.
4. Qualify the matched numerical fixture and predeclare output-specific accuracy
   thresholds before evaluating reserved outcomes. Existing convergence failures
   cannot be repaired by fitting material parameters to experimental data.

If essential metadata cannot be recovered publicly, retain this source for an
offline prediction benchmark and select another physical component dataset.
Neither guessed metadata nor a visually similar reconstructed scoop is a pass.

### Converted table consistency

On 2026-09-20, the public dataset page displayed 8,100 rows, whereas its prose
and the pinned file inventory describe 6,700 trials. Follow-up viewer metadata
shows that these counts refer to different representations. The pinned
[`dataset_info.json`](https://huggingface.co/datasets/pthangeda/scooping-dataset/blob/74f8f8ac59a78a3f3710885b56fdaf119e7605ce/scooping_dataset/dataset_info.json)
was retrieved separately. It declares integer `terrain_id` and `sample_index`,
image fields, a force CSV path, and float32 action, volume and depth-normalization
fields. It contains no row count, force acquisition metadata, or conversion
provenance. Its empty license field does not replace the repository card's
license declaration. Raw metadata and its checksum are retained in
`evidence/public-selection/scooping-feature-schema.json`.

Before importing the converted table, reconcile its actual row identities with
the 6,700-trial channel inventory and verify original-to-converted equality.
The row-count display alone cannot establish a valid split or data completeness.
No additional numerical trial outcomes were inspected for this check.

The public datasets-server `info` and `size` responses identify the default
viewer as **`imagefolder`**, with only `image` and `label` features. Its labels
are `depth_images` and `rgb_images`; both responses set `partial: true`. Thus
the displayed 8,100 image rows are not a verified row count for the saved Arrow
trial table. This is not evidence of duplicate scooping trials. The responses
are current, unpinned viewer metadata, retained with checksums in
`evidence/public-selection/scooping-viewer-schema.json`.

An importer must reject this two-column image-folder representation when a
trial table is required. Require explicit terrain/sample identifiers and the
documented action, outcome and sensor fields; do not treat the default viewer's
train split as a scientific train/test split. Actual saved-table row identities
and original-array equality still need verification.

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

### Recovered project report

The [TIB report](https://oa.tib.eu/renate/handle/123456789/35121) was successfully
downloaded on 2026-09-20 (178 pages; retrieval manifest in
`docs/evidence/public-selection/rwth-report-retrieval.json`). Pages 38–40 describe
four draw-wire sensors and 24 MH-4 CAN pressure sensors. Figure 20, visually
inspected, distinguishes cylinder-side and valve-side pressures and includes an
adjustable-boom circuit in addition to boom, stick, bucket and swing.

This requires an adjustable-boom machine configuration and explicit sensor-location
mapping; the present bench articulation is insufficient. The schematic supplies
topology, not cylinder areas, pivot dimensions or calibrated channel identities.
The earlier demonstrator's stated processing capacity of up to 1 kHz must not be
used as the Volvo recording's verified sampling frequency.

Page 42 reports approximately 2 cm average static and 5 cm average dynamic
camera/environment reconstruction accuracy. Those aggregate results are not
per-sample uncertainty bounds or independent bucket-force validation. Appendix
page 175 identifies the Volvo pilots with the Nörvenich gravel pit; the selected
pickle's trial-to-site mapping still needs verification.

Next admission requirement: obtain the raw data dictionary and match its actual
channels to this topology before any pressure-to-force reconstruction. Report
access has been resolved; dataset-file access has not.

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
