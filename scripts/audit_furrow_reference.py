"""Verify the public furrow archive and partition without reading terrain outcomes."""

import argparse
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path


def audit(archive, evidence):
    record_bytes = (evidence / "furrows-record.json").read_bytes()
    record = json.loads(record_bytes)
    admission = json.loads((evidence / "furrows-admission.json").read_text())
    inventory = json.loads((evidence / "furrows-sand-inventory.json").read_text())
    split = json.loads((evidence / "furrows-split.json").read_text())
    assert hashlib.sha256(record_bytes).hexdigest() == admission["record_sha256"]
    assert record["id"] == split["record_id"] == inventory["record_id"] == 21159754
    assert record["metadata"]["license"]["id"] == "cc-by-4.0"
    source = next(f for f in record["files"] if f["key"] == "Sand_0.3-1_mm.zip")
    md5, sha = hashlib.md5(), hashlib.sha256()
    with archive.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            md5.update(block)
            sha.update(block)
    assert "md5:" + md5.hexdigest() == source["checksum"]
    assert archive.stat().st_size == source["size"] == inventory["archive_bytes"]
    assert sha.hexdigest() == inventory["archive_sha256"] == split["archive_sha256"]
    trials, meshes = [], []
    with zipfile.ZipFile(archive) as package:
        entries = [dict(path=i.filename, bytes=i.file_size, crc32=i.CRC)
                   for i in package.infolist()]
        assert entries == inventory["entries"]
        assert len({e["path"] for e in entries}) == len(entries)
        for item in entries:
            parts = item["path"].split("/")
            if len(parts) == 6 and parts[4] == "OBJ_raw" and parts[5].endswith(".obj"):
                trial = dict(path=item["path"], tool=parts[1], speed_setting=parts[2],
                             weights=int(parts[3]), repeat=parts[5][:-4])
                trial["role"] = ("development" if parts[1] == "Skis_without_active_elements"
                                 and parts[2] == "5Hz" else "reserved")
                trials.append(trial)
        assert trials == split["trials"]
        groups = {}
        for trial in trials:
            key = (trial["tool"], trial["speed_setting"], trial["weights"])
            groups.setdefault(key, []).append(trial)
        assert len(groups) == 30
        for (tool, speed, weights), group in groups.items():
            assert tool in ("Skis_without_active_elements", "Skis_with_active_elements")
            assert speed in ("5Hz", "10Hz", "15Hz") and weights in range(5)
            assert sorted(x["repeat"] for x in group) == ["1", "2", "3", "4", "5"]
            assert len({x["role"] for x in group}) == 1
        assert sum(t["role"] == "development" for t in trials) == 25
        assert sum(t["role"] == "reserved" for t in trials) == 125
        for name in ("Skis_without_active_elements", "Skis_with_active_elements"):
            path = f"Sand_0.3-1_mm/{name}/{name}.stl"
            # Read only tool geometry. No scan, texture, or outcome is decompressed.
            raw = package.read(path)
            count = struct.unpack_from("<I", raw, 80)[0]
            assert len(raw) == 84 + 50 * count
            vertices = []
            for i in range(count):
                vertices.extend(struct.unpack_from("<9f", raw, 96 + 50 * i))
            assert all(math.isfinite(v) for v in vertices)
            meshes.append(dict(path=path, sha256=hashlib.sha256(raw).hexdigest(),
                               triangles=count, units="not established",
                               bounds=[[min(vertices[a::3]), max(vertices[a::3])]
                                       for a in range(3)]))
    return dict(archive_integrity=True, partition_integrity=True, trials=len(trials),
                development_trials=25, reserved_trials=125, meshes=meshes,
                outcomes_read=False, physical_validation=False,
                limitation="File identity and grouping do not establish measurement accuracy")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        default=Path("data/raw/admission/public-selection/furrows-sand-fine.zip"))
    parser.add_argument("--evidence", type=Path, default=Path("docs/evidence/public-selection"))
    args = parser.parse_args()
    print(json.dumps(audit(args.archive, args.evidence), indent=2, allow_nan=False))
