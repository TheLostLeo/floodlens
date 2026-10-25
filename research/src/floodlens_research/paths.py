from __future__ import annotations

from pathlib import Path


def repository_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "compose.yaml").is_file() and (candidate / "research").is_dir():
            return candidate
    raise RuntimeError("Could not locate FloodLens repository root")


def research_data_root() -> Path:
    return repository_root() / "data" / "research"


def artifacts_root() -> Path:
    path = repository_root() / "research" / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path
