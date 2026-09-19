"""Bounded raw intrusion trial reader; no inferred units or surface alignment."""

import csv
import hashlib
import io
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np


def parse_trial(payload: bytes) -> dict:
    if len(payload) > 30_000_000:
        raise ValueError("trial exceeds admission bound")
    lines = [line for line in payload.decode("utf-8-sig").splitlines() if line.strip()]
    rows = list(csv.reader(lines))
    if len(rows) < 5:
        raise ValueError("missing metadata or samples")
    keys, values, columns = rows[:3]
    if (
        len(keys) != len(values)
        or len(set(keys)) != len(keys)
        or len(set(columns)) != len(columns)
        or "time" not in columns
    ):
        raise ValueError("invalid metadata or sample header")
    if any(len(row) != len(columns) for row in rows[3:]):
        raise ValueError("sample width mismatch")
    try:
        samples = np.asarray(rows[3:], dtype=np.float64)
    except ValueError as error:
        raise ValueError("nonnumeric sample") from error
    if not np.isfinite(samples).all():
        raise ValueError("nonfinite sample")
    time = samples[:, columns.index("time")]
    if np.any(np.diff(time) <= 0):
        raise ValueError("sample times must strictly increase")
    return {
        "metadata": dict(zip(keys, values, strict=True)),
        "columns": columns,
        "samples": samples,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "units": "Raw source channels; units and calibration require separate admission",
        "surface_alignment": None,
        "excluded_samples": 0,
    }


def load_development_trial(root: Path, manifest: dict, member: str) -> dict:
    """Only calibration/development partitions are accessible through this API."""
    matches = [r for r in manifest["trials"] if r["member"] == member]
    if len(matches) != 1:
        raise ValueError("unknown or ambiguous trial")
    record = matches[0]
    if record["partition"] not in ("calibration", "development"):
        raise ValueError("trial is reserved; independent evaluation is not yet admitted")
    archive_name = record["archive"]
    if PurePosixPath(archive_name).name != archive_name or "\\" in archive_name:
        raise ValueError("invalid archive path")
    archive_path = root / archive_name
    if not archive_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("archive escapes source root")
    if archive_path.stat().st_size > 30_000_000:
        raise ValueError("archive exceeds admission bound")
    payload = archive_path.read_bytes()
    expected = [r for r in manifest["files"] if r["path"] == archive_name]
    if len(expected) != 1 or hashlib.sha256(payload).hexdigest() != expected[0]["sha256"]:
        raise ValueError("archive checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        matches = [i for i in archive.infolist() if i.filename == member]
        if len(matches) != 1 or matches[0].file_size > 30_000_000:
            raise ValueError("duplicate or oversized trial")
        payload = archive.read(matches[0])
    if hashlib.sha256(payload).hexdigest() != record["sha256"]:
        raise ValueError("trial checksum mismatch")
    result = parse_trial(payload)
    result.update(partition=record["partition"], member=member)
    return result
