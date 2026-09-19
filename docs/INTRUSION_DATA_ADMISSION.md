# Individual intrusion trials: admission audit

Status: **provisional source inventory, not admitted physical validation**.

The [public repository](https://github.com/johnruck-sed/UnifiedGranularIntrusionDynamics)
is pinned at `1c6056044728484836075e954d6ff1e768ab7280`.
Seven downloaded files match their Git blob hashes. The committed
`evidence/intrusion-2025/source-manifest.json` records SHA-256 hashes for these
files and 145 top-level CSV members across three archives. Nested archives are
not unpacked or counted as trials. Source notebooks are inspected as text only.
No explicit repository data license has been established; raw files stay local.

```sh
python scripts/fetch_validation_sources.py --source intrusion-2025
python scripts/audit_intrusion_sources.py --output runs/intrusion-source-audit.json
```

The inventory command defaults to the committed pinned source tree and refuses
to overwrite an existing audit output.

## Partition frozen before numeric inspection

For each of the sand filename labels `T2_V056` and `T2_V057`:

| Replicate label | Provisional role |
|---|---|
| 1, 2 | Calibration |
| 3 | Development |
| 4, 5 | Holdout |

All other trials remain reserved and unassigned. These are filename identities,
not verified measurements of packing fraction. The ten selected payloads have
distinct hashes. Numeric outcomes from the four held-out files have not been
inspected. The reader rejects reserved partitions. This software guard prevents
accidental access; it is not a security boundary against someone changing the code
or manifest. Final acceptance criteria and transforms must be frozen separately
before evaluation. These physical partitions are independent of policy-training
scenario partitions.

## Primary methods and unresolved correspondence

The [author-uploaded preprint, Materials and Methods](https://www.researchgate.net/publication/396154401_Unified_Granular_Intrusion_Dynamics_for_Planetary_Materials)
describes a 12.7 mm cylindrical intruder, 20 mm/s penetration, 100 mm maximum
depth, and force inferred from motor current and leg kinematics. It states that
frictional beds are fluidized before each test and that four intrusions are
averaged per packing condition. This supports a preparation protocol, but the
selected repository groups contain five files each. The exact correspondence
between files and published averages remains unresolved. The preprint describes
300 Hz acquisition; these six raw files have median timestamp increments near
2.22–2.25 ms. Actual timestamps must be retained.

## Direct checks on calibration/development files

All six pass finite numeric, consistent-column and strictly increasing timestamp
checks. No samples were filtered, aligned, excluded or interpolated.

- Both columns named as load-cell channels contain only zeros. They must not be
  represented as direct force measurements.
- `state flag` is always zero and cannot identify intrusion phases.
- The current-derived force channel includes negative readings and plateaus.
  A sample count does not establish independent sensor observations.
- The first second includes motion. Its force scatter is not an unloaded static
  sensor uncertainty estimate.
- The upstream notebook uses fixed sample-index slices and trial-specific surface
  offsets. These are not imported automatically into the testbed.
- Measured position is available, but the mapping to tip depth needs a justified
  surface datum and uncertainty. Metadata field units require verification.

## Requirements before admission

1. Reconcile trial selection with the reported protocol and document any exclusions
   using reasons independent of agreement with simulation.
2. Establish force calibration, bias/gravity treatment, bandwidth and uncertainty;
   repeated trials alone cannot bound systematic sensor error.
3. Verify geometry, chamber boundaries, packing, surface datum and measured-motion
   transforms for the selected trials.
4. Freeze preprocessing, useful acceptance criteria and calibration parameters.
5. Resolve numerical convergence before opening the holdout for acceptance.

The presence of a surface-displacement notebook does not establish availability
of the raw laser profiles it references. This inventory does not admit terrain
measurements. This dataset also does not validate excavator hydraulics, bucket
transport, multi-tool interaction or transfer to customer worksites.
