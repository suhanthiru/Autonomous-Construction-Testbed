"""Checksummed, compressed transition shards with numeric columns and lossless records."""

import hashlib
import json
from pathlib import Path

import numpy as np

from excavation_sim.episodes import load_episode
from excavation_sim.provenance import canonical_json


def export_episode(source: Path, destination: Path, chunk_size=256):
    if type(chunk_size) is not int or chunk_size < 1:
        raise ValueError("positive chunk size required")
    transitions = load_episode(source)
    destination.mkdir(parents=True, exist_ok=False)
    records = [json.loads(line) for line in (source / "transitions.jsonl").read_text().splitlines()]
    shards = []
    for start in range(0, len(records), chunk_size):
        rows = records[start : start + chunk_size]
        encoded = [canonical_json(row).encode("utf-8") for row in rows]
        offsets = np.cumsum([0] + [len(row) for row in encoded], dtype=np.int64)
        path = destination / f"chunk-{len(shards):05d}.npz"
        commands = [list(row["command"].values())[0] for row in rows]
        np.savez_compressed(
            path,
            records_utf8=np.frombuffer(b"".join(encoded), dtype=np.uint8),
            offsets=offsets,
            tick=np.array([row["observation"]["tick"] for row in rows], dtype=np.int64),
            time_s=np.array([row["observation"]["time_s"] for row in rows]),
            tool_position_m=np.array([row["observation"]["tool_position_m"] for row in rows]),
            command=np.asarray(commands, dtype=np.float64),
        )
        shards.append(
            {
                "file": path.name,
                "rows": len(rows),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    index = {
        "schema": "packed-transitions-v1",
        "transitions": len(transitions),
        "source_manifest": json.loads((source / "manifest.json").read_text()),
        "source_transitions_sha256": hashlib.sha256(
            (source / "transitions.jsonl").read_bytes()
        ).hexdigest(),
        "observation_access": "policy observations and executed commands only",
        "shards": shards,
    }
    (destination / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def iter_records(directory: Path):
    index = json.loads((directory / "index.json").read_text(encoding="utf-8"))
    if index["schema"] != "packed-transitions-v1":
        raise ValueError("unsupported packed dataset schema")
    count = 0
    last = None
    for shard in index["shards"]:
        path = (directory / shard["file"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("external shard path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != shard["sha256"]:
            raise ValueError("dataset checksum mismatch")
        with np.load(path, allow_pickle=False) as data:
            payload, offsets = data["records_utf8"], data["offsets"]
            if (
                payload.dtype != np.uint8
                or offsets.dtype != np.int64
                or offsets.shape != (shard["rows"] + 1,)
                or offsets[0] != 0
                or offsets[-1] != len(payload)
                or not (np.diff(offsets) > 0).all()
            ):
                raise ValueError("invalid packed record offsets")
            for a, b in zip(offsets[:-1], offsets[1:], strict=True):
                row = json.loads(payload[a:b].tobytes())
                if last is not None and row["observation"] != last:
                    raise ValueError("discontinuous packed episode")
                last = row["next_observation"]
                count += 1
                yield row
    if count != index["transitions"]:
        raise ValueError("packed episode length mismatch")
