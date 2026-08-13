from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_settings(path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        settings = yaml.safe_load(handle) or {}
    return settings
