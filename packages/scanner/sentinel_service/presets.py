"""Named identity presets so the dashboard can launch a demo in one click."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SCANNER_ROOT = Path(__file__).resolve().parent.parent
PRESET_FILES = {
    "shopapi": SCANNER_ROOT / "configs" / "shopapi.identities.yaml",
    "bankapi": SCANNER_ROOT / "configs" / "bankapi.identities.yaml",
}


def resolve_identities_file(
    preset: str | None,
    identities_config: dict[str, Any] | list[dict[str, Any]] | None,
    dest_dir: Path,
) -> Path:
    """Return a YAML path the engine can load.

    Presets: ``shopapi`` (ShopAPI) and ``bankapi`` (BankAPI).
    A raw ``identities_config`` is written to a temp file next to the DB.
    """
    if identities_config is not None:
        payload: dict[str, Any]
        if isinstance(identities_config, list):
            payload = {"identities": identities_config}
        else:
            payload = identities_config
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "identities.override.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return path

    name = (preset or "shopapi").lower()
    if name not in PRESET_FILES:
        known = ", ".join(sorted(PRESET_FILES))
        raise ValueError(f"Unknown identities preset {name!r}. Known: {known}")
    path = PRESET_FILES[name]
    if not path.is_file():
        raise FileNotFoundError(f"Preset file missing: {path}")
    return path
