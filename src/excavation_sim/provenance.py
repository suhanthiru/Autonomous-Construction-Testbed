"""Portable run identity, independent of a particular physics engine."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(json_value(v) for v in value)
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(json_value(value), sort_keys=True, allow_nan=False, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def source_identity(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-c", "core.excludesFile=", *args],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    # Include uncommitted and untracked source, not just git diff (which misses new files).
    hashes = {}
    for folder in ("src", "configs", "experiments", "scripts"):
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    for name in ("pyproject.toml", "requirements-lock.txt"):
        path = root / name
        if path.exists():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "revision": git("rev-parse", "HEAD"),
        "working_tree_status": git("status", "--porcelain"),
        "source_sha256": fingerprint(hashes),
        "files": hashes,
    }


def environment_info() -> dict[str, Any]:
    packages = {}
    for name in ("excavation-sim", "newton", "warp-lang", "numpy"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": sys.version, "platform": platform.platform(), "packages": packages}
