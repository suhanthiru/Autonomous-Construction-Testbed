"""Explicit public-data transforms; no upstream code or pickles are executed."""

import csv
import hashlib
from pathlib import Path

import numpy as np


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rheometer_volume_fraction(path: Path) -> dict:
    """Reproduce the published notebook's two pressure/depth transformations.

    These are two packing conditions, not identified independent repeat trials.
    Retain all samples, including negative depths after the published surface shift.
    """
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    result = {"sha256": file_hash(path), "conditions": []}
    radius, area = 0.00635, 0.00016129
    for label, offset, packing in [("phi057", 0, 0.57), ("phi059", 3, 0.59)]:
        pairs = [
            (float(row[offset]), float(row[offset + 1]))
            for row in rows
            if row[offset].strip() and row[offset + 1].strip()
        ]
        values = np.asarray(pairs)
        if not len(values) or not np.isfinite(values).all():
            raise ValueError("invalid force/depth samples")
        result["conditions"].append(
            {
                "id": label,
                "packing_fraction": packing,
                "depth_m": (values[:, 0] - 1.5 * radius).tolist(),
                "resisting_force_n": (-values[:, 1]).tolist(),
                "dimensionless_depth": (values[:, 0] / radius - 1.5).tolist(),
                "dimensionless_pressure": (
                    -values[:, 1] / (area * 2500 * packing * 9.8 * radius)
                ).tolist(),
            }
        )
    return result


def read_triangle_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append([float(v) for v in parts[1:4]])
        elif parts[0] == "f":
            indices = [int(p.split("/")[0]) for p in parts[1:]]
            if len(indices) < 3 or any(i <= 0 or i > len(vertices) for i in indices):
                raise ValueError("unsupported or invalid OBJ face")
            for i in range(1, len(indices) - 1):
                faces.extend([indices[0] - 1, indices[i] - 1, indices[i + 1] - 1])
    points = np.asarray(vertices, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all() or not faces:
        raise ValueError("invalid triangle mesh")
    return points, np.asarray(faces, dtype=np.int32)


def ddbot_actions(root: Path, trial: int) -> np.ndarray:
    if trial not in (0, 1):
        raise ValueError("DDBot system identification trial must be 0 or 1")
    path = root / f"data/trajectories/sys_id_sim_{trial}_pos-dt_0.01.npy"
    actions = np.load(path, allow_pickle=False)
    if actions.ndim != 2 or actions.shape[1] != 6 or not np.isfinite(actions).all():
        raise ValueError("invalid DDBot actions")
    # Despite the filename, upstream position control interprets these as increments.
    return actions


def surface_height_map(points: np.ndarray, radius: float, resolution: int = 40) -> np.ndarray:
    """DDBot's 24 cm region centered at (0.2, 0.2); x is the first array axis.

    Deposit center heights into center and four radius-offset pixels. Explicitly
    crop to valid indices rather than relying on out-of-bounds kernel behavior.
    """
    heights = np.zeros((resolution, resolution), dtype=np.float64)
    pixel = 0.24 / resolution
    for dx, dy in [
        (0, 0),
        (-radius, -radius),
        (radius, radius),
        (-radius, radius),
        (radius, -radius),
    ]:
        ij = np.floor((points[:, :2] + [dx, dy] - 0.2) / pixel + resolution / 2).astype(int)
        valid = ((ij >= 0) & (ij < resolution)).all(axis=1)
        np.maximum.at(heights, (ij[valid, 0], ij[valid, 1]), points[valid, 2])
    return heights
