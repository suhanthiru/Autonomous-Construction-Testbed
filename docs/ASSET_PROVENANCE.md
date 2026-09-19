# Geometry and data provenance

The default machine, bucket, bed, rigid boxes and scenario terrain are procedural
geometry defined in repository source. The machine is a fixed-base, bench-scale
four-joint mechanism; it does not reproduce a named commercial excavator or its
hydraulics. Runtime metadata records generated geometry, mass and actuator parameters.

The optional DDBot terrain replay uses a pinned external shovel geometry and public
measurements. Source revision, transformations and admitted trial roles are documented
in `DATA_ADMISSION.md` and `TERRAIN_PROTOCOL.md`; its MIT notice is preserved under
`licenses/DDBot-MIT.txt`. It is not the default procedural machine asset.

The rheometer replay's source has no explicit repository redistribution license.
Raw curves are not bundled here. The fetch/admission workflow preserves source hashes
and transformations locally; see `DATA_ADMISSION.md` and `FORCE_REPLAY.md`.

Recorded synthetic demonstration shards and baseline checkpoints contain this
testbed's outputs, with their original source manifests. They are not measured
physical ground truth. Third-party runtime packages retain their own licenses;
`requirements-lock.txt` identifies the executed package versions.
