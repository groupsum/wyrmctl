from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    documents: list[tuple[Path, dict[str, object]]] = []
    registry = Registry()
    for path in sorted((ROOT / "schemas" / "wyrmctl").glob("*.schema.json")):
        with path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
        Draft202012Validator.check_schema(schema)
        documents.append((path, schema))
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(path.name, resource)
        if "$id" in schema:
            registry = registry.with_resource(str(schema["$id"]), resource)
    for _path, schema in documents:
        Draft202012Validator(schema, registry=registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
