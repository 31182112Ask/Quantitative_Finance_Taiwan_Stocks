from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEZONE = "Asia/Taipei"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path = PROJECT_ROOT
    config: Path = PROJECT_ROOT / "config"
    data: Path = PROJECT_ROOT / "data"
    reports: Path = PROJECT_ROOT / "reports"
    logs: Path = PROJECT_ROOT / "logs"


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {file_path}")
    return data


def ensure_project_dirs(paths: ProjectPaths | None = None) -> None:
    paths = paths or ProjectPaths()
    for folder in [
        paths.data / "raw",
        paths.data / "processed",
        paths.data / "intraday",
        paths.data / "daily",
        paths.reports / "daily",
        paths.reports / "intraday",
        paths.reports / "paper_trading",
        paths.logs,
    ]:
        folder.mkdir(parents=True, exist_ok=True)
