"""Repository manifest loading and environment isolation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from wyrmctl.contracts import BUILTIN_CONTRACTS, check_document, semantic_digest
from wyrmctl.errors import ValidationError
from wyrmctl.profile import current_profile


@dataclass(frozen=True, slots=True)
class RepositoryEnvironment:
    name: str
    desired_state: dict[str, Path]


@dataclass(frozen=True, slots=True)
class RepositoryManifest:
    name: str
    root: Path
    owners: tuple[str, ...]
    environments: dict[str, RepositoryEnvironment]
    domains: tuple[str, ...]
    raw: dict[str, Any]

    @property
    def digest(self) -> str:
        return semantic_digest(self.raw)

    def environment(self, name: str) -> RepositoryEnvironment:
        try:
            return self.environments[name]
        except KeyError as exc:
            raise ValidationError(f"unknown repository environment: {name}") from exc


def load_repository(path: str | Path) -> RepositoryManifest:
    source = Path(path)
    raw = _read_mapping(source)
    check_document(raw, BUILTIN_CONTRACTS)
    if raw.get("kind") != "NpmctlRepository":
        raise ValidationError("repository manifest kind must be NpmctlRepository")
    metadata = _mapping(raw.get("metadata"), "metadata")
    spec = _mapping(raw.get("spec"), "spec")
    name = metadata.get("name")
    if not isinstance(name, str) or not name:
        raise ValidationError("repository metadata.name must be a non-empty string")
    owners = _strings(spec.get("owners"), "spec.owners")
    domains = tuple(
        sorted({str(item["name"]).lower().rstrip(".") for item in _mappings(spec.get("domains", []), "spec.domains")})
    )
    root = (
        source.resolve().parent.parent
        if source.parent.name == current_profile().repository_dir
        else source.resolve().parent
    )
    environments: dict[str, RepositoryEnvironment] = {}
    for env_name, env_value in _mapping(spec.get("environments"), "spec.environments").items():
        if not isinstance(env_name, str) or not env_name:
            raise ValidationError("repository environment names must be non-empty strings")
        env = _mapping(env_value, f"spec.environments.{env_name}")
        refs = _mapping(env.get("desiredState"), f"spec.environments.{env_name}.desiredState")
        resolved: dict[str, Path] = {}
        for key, relative in refs.items():
            if not isinstance(relative, str) or not relative:
                raise ValidationError(f"desired-state reference {env_name}.{key} must be a non-empty string")
            target = (source.parent / relative).resolve()
            if source.parent.resolve() not in target.parents:
                raise ValidationError(f"desired-state reference escapes {current_profile().repository_dir}: {relative}")
            if not target.is_file():
                raise ValidationError(f"desired-state reference does not exist: {relative}")
            resolved[str(key)] = target
        environments[env_name] = RepositoryEnvironment(env_name, resolved)
    if not environments:
        raise ValidationError("repository must declare at least one environment")
    return RepositoryManifest(name, root, owners, environments, domains, raw)


def repository_document(
    name: str, *, owners: list[str], environments: dict[str, dict[str, str]], domains: list[str]
) -> dict[str, Any]:
    return {
        "apiVersion": current_profile().api_version,
        "kind": "NpmctlRepository",
        "schemaVersion": 1,
        "metadata": {"name": name},
        "spec": {
            "owners": sorted(set(owners)),
            "environments": {key: {"desiredState": value} for key, value in sorted(environments.items())},
            "domains": [{"name": domain} for domain in sorted(set(domains))],
        },
    }


def _read_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"repository manifest does not exist: {path}")
    try:
        value = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.suffix == ".json"
            else yaml.safe_load(path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValidationError(f"failed to read repository manifest {path}: {exc}") from exc
    return _mapping(value, str(path))


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    return dict(value)


def _mappings(value: Any, path: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be an array")
    return [_mapping(item, f"{path}[{index}]") for index, item in enumerate(value)]


def _strings(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValidationError(f"{path} must be a non-empty string array")
    return tuple(sorted(set(value)))
