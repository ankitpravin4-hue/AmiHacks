"""Identity matrix: who may legitimately access which objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from sentinel_core.models import Identity


class CrossAccessCase(BaseModel):
    """Attacker A tries to access an object that identity B owns."""

    attacker: Identity
    owner: Identity
    object_type: str
    object_id: int | str


def object_type_from_param(param_name: str) -> str:
    """Map a path param to an ownership key: ``order_id`` → ``order``."""
    name = param_name.lower()
    if name == "id":
        return "id"
    if name.endswith("_id"):
        return name[: -len("_id")]
    return name


def _coerce_id(value: object) -> int | str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return str(value)


class IdentityProvider:
    """Loaded test identities plus helpers for cross-identity probes."""

    def __init__(self, identities: list[Identity]) -> None:
        if not identities:
            raise ValueError("IdentityProvider requires at least one identity")
        self._by_name = {identity.name: identity for identity in identities}

    @classmethod
    def from_file(cls, path: str | Path) -> IdentityProvider:
        """Load identities from a YAML or JSON config file."""
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Identity config must be a mapping: {path}")
        return cls.from_config(data)

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> IdentityProvider:
        """Build from an already-parsed config mapping."""
        rows = data.get("identities")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Config must contain a non-empty `identities` list")
        identities: list[Identity] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Each identity must be a mapping")
            owns_raw = row.get("owns") or {}
            owns: dict[str, list[int | str]] = {}
            if isinstance(owns_raw, dict):
                for obj_type, ids in owns_raw.items():
                    owns[str(obj_type)] = [_coerce_id(item) for item in (ids or [])]
            identities.append(
                Identity(
                    name=str(row["name"]),
                    headers={str(k): str(v) for k, v in (row.get("headers") or {}).items()},
                    owns=owns,
                    is_admin=bool(row.get("is_admin", False)),
                )
            )
        return cls(identities)

    def get(self, name: str) -> Identity:
        """Return the named identity or raise ``KeyError``."""
        try:
            return self._by_name[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._by_name))
            raise KeyError(f"Unknown identity {name!r}. Known: {known}") from exc

    def all(self) -> list[Identity]:
        """Identities in config order."""
        return list(self._by_name.values())

    def authed_headers(self, identity_name: str) -> dict[str, str]:
        """Return the auth headers configured for ``identity_name``."""
        return dict(self.get(identity_name).headers)

    def owned_ids(self, identity_name: str, object_type: str) -> list[int | str]:
        """Object ids this identity legitimately owns for ``object_type``."""
        return list(self.get(identity_name).owns.get(object_type, []))

    def pick_owned(self, identity_name: str, object_type: str) -> int | str:
        """Pick one object owned by identity B for a later cross-access test.

        Detectors call this for identity B, then request that object as
        identity A via :meth:`authed_headers`.
        """
        ids = self.owned_ids(identity_name, object_type)
        if not ids:
            raise ValueError(f"{identity_name} owns no {object_type!r} objects")
        return ids[0]

    def cross_access_cases(self, object_type: str) -> list[CrossAccessCase]:
        """Every (attacker, owner, object_id) where attacker is not the owner.

        This is the identity matrix expansion used by the BOLA detector.
        """
        cases: list[CrossAccessCase] = []
        identities = self.all()
        for owner in identities:
            for object_id in owner.owns.get(object_type, []):
                for attacker in identities:
                    if attacker.name == owner.name:
                        continue
                    cases.append(
                        CrossAccessCase(
                            attacker=attacker,
                            owner=owner,
                            object_type=object_type,
                            object_id=object_id,
                        )
                    )
        return cases
