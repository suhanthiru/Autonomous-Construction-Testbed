"""Fetch a bounded set of public source files without executing third-party code."""

import hashlib
import json
import urllib.request
from pathlib import Path

SOURCES = {
    "rheometer": "johnruck-sed/GRL_2023_RobotRheometer",
    "ddbot": "IanYangChina/DDBot-IEEE-TRO-2025",
}
REVISIONS = {
    "rheometer": "f4b98b71162ab4400fb3ad3bedb38a4b71a3a8b1",
    "ddbot": "e642f7c73f37539c21161bd29669fa8d91912b88",
}
METADATA = {
    "scripts/run_si.py",
    "simulator/doma/envs/planting_env.py",
    "simulator/doma/envs/planting_env_v1.py",
    "simulator/doma/engine/manipulator/effector.py",
    "simulator/doma/engine/object/mesh.py",
    "simulator/doma/engine/utils/transform_ti.py",
    "simulator/doma/engine/loss_function/pcd_emd_hm_loss.py",
    "simulator/doma/engine/configs/manipulator_cfgs/shovel_eef.yaml",
    "simulator/doma/assets/meshes/processed/ShovelEEF-ShovelEEF.obj",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "excavation-validation-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(30_000_001)
    if len(data) > 30_000_000:
        raise ValueError("asset exceeds admission download limit")
    return data


def main():
    root = Path("data/raw/admission")
    root.mkdir(parents=True, exist_ok=True)
    for name, repository in SOURCES.items():
        commit = json.loads(
            fetch(f"https://api.github.com/repos/{repository}/commits/{REVISIONS[name]}")
        )
        revision = commit["sha"]
        if revision != REVISIONS[name]:
            raise ValueError("source revision mismatch")
        tree = json.loads(
            fetch(f"https://api.github.com/repos/{repository}/git/trees/{revision}?recursive=1")
        )
        if tree.get("truncated"):
            raise ValueError("incomplete source inventory")
        manifest = {
            "repository": repository,
            "revision": revision,
            "tree_sha": tree["sha"],
            "files": [],
            "skipped": [],
            "inventory": tree["tree"],
        }
        folder = root / name / revision
        folder.mkdir(parents=True, exist_ok=True)
        for entry in tree["tree"]:
            path = entry["path"]
            selected = path in {"README.md", "LICENSE"}
            if name == "rheometer":
                selected |= path.startswith(("lab_data/", "matlab_files/"))
                selected |= path == "jupyter_notebooks/Robot_Geometric_Trials.ipynb"
            else:
                selected |= path in METADATA
                selected |= path.startswith(
                    ("data/trajectories/", "data/system-identification-targets/sand/")
                )
            if not selected or entry["type"] != "blob":
                continue
            output = folder / path
            if not output.resolve().is_relative_to(folder.resolve()):
                raise ValueError("source path escapes destination")
            url = f"https://raw.githubusercontent.com/{repository}/{revision}/{path}"
            data = fetch(url)
            git_blob = b"blob " + str(len(data)).encode() + b"\0" + data
            if hashlib.sha1(git_blob).hexdigest() != entry["sha"]:
                raise ValueError(f"Git blob hash mismatch: {path}")
            lfs = data.startswith(b"version https://git-lfs.github.com/spec/v1")
            if lfs:
                pointer = data.decode().splitlines()
                size = int(next(line.split()[1] for line in pointer if line.startswith("size ")))
                if size > 30_000_000:
                    manifest["skipped"].append(
                        {"path": path, "size": size, "reason": "over 30 MB admission limit"}
                    )
                    continue
                expected = next(
                    line.split(":", 1)[1] for line in pointer if line.startswith("oid ")
                )
                url = f"https://media.githubusercontent.com/media/{repository}/{revision}/{path}"
                data = fetch(url)
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError(f"LFS hash mismatch: {path}")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                if output.read_bytes() != data:
                    raise ValueError(f"refusing to overwrite different source bytes: {path}")
            else:
                output.write_bytes(data)
            manifest["files"].append(
                {
                    "path": path,
                    "url": url,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "lfs": lfs,
                }
            )
        (folder / "admission-manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(name, revision, len(manifest["files"]), "files", flush=True)


if __name__ == "__main__":
    main()
