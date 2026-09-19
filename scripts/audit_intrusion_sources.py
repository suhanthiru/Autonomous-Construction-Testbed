"""Inventory pinned intrusion archives without exposing held-out sample values.

No source notebooks are executed, and archive members are never extracted.
The split is provisional: admission and physical acceptance remain separate gates.
"""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

REVISION = "1c6056044728484836075e954d6ff1e768ab7280"
REPOSITORY = "johnruck-sed/UnifiedGranularIntrusionDynamics"


def audit(root, tree):
    if tree.get("truncated") or tree["sha"] != REVISION:
        raise ValueError("incomplete or incorrect source tree")
    entries = {e["path"]: e for e in tree["tree"] if e["type"] == "blob"}
    files, trials = [], []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name not in entries:
            continue
        if path.stat().st_size > 30_000_000:
            raise ValueError("source file exceeds admission bound")
        data = path.read_bytes()
        blob = b"blob " + str(len(data)).encode() + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != entries[path.name]["sha"]:
            raise ValueError(f"Git blob mismatch: {path.name}")
        files.append(
            {
                "path": path.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "git_blob_sha1": entries[path.name]["sha"],
                "bytes": len(data),
            }
        )
        if path.suffix != ".zip":
            continue
        with zipfile.ZipFile(path) as archive:
            seen, total = set(), 0
            for info in archive.infolist():
                name = info.filename
                parts = PurePosixPath(name)
                if (
                    parts.is_absolute()
                    or ".." in parts.parts
                    or "\\" in name
                    or ":" in name
                    or name in seen
                ):
                    raise ValueError("unsafe or duplicate archive member")
                seen.add(name)
                total += info.file_size
                if info.file_size > 30_000_000 or total > 300_000_000:
                    raise ValueError("archive exceeds admission bound")
                if info.is_dir() or not name.endswith(".csv"):
                    continue
                payload = archive.read(info)  # Hash only; do not inspect outcomes.
                match = re.match(r"(T2|GB)_V(\d+)_(\d+)_", parts.name)
                row = {
                    "archive": path.name,
                    "member": name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "partition": "reserved_unassigned",
                }
                if match:
                    material, packing_label, replicate = match.groups()
                    replicate = int(replicate)
                    row.update(
                        material_label=material,
                        packing_label=packing_label,
                        replicate_label=replicate,
                    )
                    # Preserve exact filename labels, not inferred measured packing.
                    if material == "T2" and packing_label in ("056", "057"):
                        row["partition"] = {
                            1: "calibration",
                            2: "calibration",
                            3: "development",
                            4: "holdout",
                            5: "holdout",
                        }.get(replicate, "reserved_unassigned")
                trials.append(row)
    selected = [r for r in trials if r["partition"] != "reserved_unassigned"]
    identities = {(r["material_label"], r["packing_label"], r["replicate_label"]) for r in selected}
    if len(selected) != 10 or len(identities) != 10:
        raise ValueError("expected ten distinct provisional sand trials")
    if len({r["sha256"] for r in selected}) != len(selected):
        raise ValueError("duplicate payload across provisional physical partitions")
    return {
        "repository": REPOSITORY,
        "revision": REVISION,
        "files": files,
        "trials": trials,
        "physical_admission": "not_assessed",
        "split_basis": "Filename identities only, frozen before inspecting numeric outcomes. "
        "Calibration 1/2, development 3, holdout 4/5 for T2 V056 and V057. "
        "Distinct trial labels do not establish independent bed preparation.",
        "redistribution": "No explicit repository license established; raw files remain local.",
        "transform": "None. No outliers excluded or surface offsets fitted.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("data/raw/admission/intrusion-2025") / REVISION
    )
    parser.add_argument("--tree", type=Path,
                        default=Path("docs/evidence/intrusion-2025/source-tree.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, json.loads(args.tree.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(f"Verified {len(result['files'])} files; inventoried {len(result['trials'])} trials")


if __name__ == "__main__":
    main()
