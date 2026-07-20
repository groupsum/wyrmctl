"""Operational report and compliance artifact helpers."""

from __future__ import annotations

import hashlib
import json
import ast
import os
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from wyrmctl.planner import Plan
from wyrmctl.profile import current_profile


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def write_state_backup(directory: str | Path, existing_state: Any) -> Path:
    payload = {
        "created_at": utc_now(),
        "existing": [resource.to_dict() for resource in existing_state.resources()],
    }
    name = f"{current_profile().name}-state-{hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]}.json"
    return write_json(Path(directory) / name, payload)


def rollback_plan(plan: Plan) -> dict[str, Any]:
    """Generate a best-effort rollback plan from planned mutations."""

    steps: list[dict[str, Any]] = []
    for operation in plan.operations:
        if operation.action == "create" and operation.desired is not None:
            steps.append({"action": "delete", "kind": operation.kind.value, "resource_id": operation.resource_id})
        elif operation.action in {"update", "adopt"} and operation.existing is not None:
            steps.append(
                {
                    "action": "restore",
                    "kind": operation.kind.value,
                    "resource_id": operation.resource_id,
                    "existing_id": operation.existing.id,
                    "payload": operation.existing.raw,
                }
            )
        elif operation.action == "delete" and operation.existing is not None:
            steps.append(
                {
                    "action": "recreate",
                    "kind": operation.kind.value,
                    "resource_id": operation.resource_id,
                    "payload": operation.existing.raw,
                }
            )
    return {"generated_at": utc_now(), "steps": steps}


def transaction_report(
    plan: Plan,
    apply_result: Any | None = None,
    *,
    dns_plan: Any | None = None,
    dns_apply_result: Any | None = None,
) -> dict[str, Any]:
    payload = plan.to_dict()
    payload["generated_at"] = utc_now()
    if apply_result is not None:
        payload["apply"] = apply_result.to_dict()
    if dns_plan is not None:
        payload["dns"] = dns_plan.to_dict()
    if dns_apply_result is not None:
        payload["dns_apply"] = dns_apply_result.to_dict()
    return payload


def drift_report(plan: Plan) -> dict[str, Any]:
    drift = [op.to_dict() for op in plan.operations if op.action in {"create", "update", "delete", "adopt"}]
    return {
        "ok": plan.ok,
        "drift_count": len(drift),
        "drift": drift,
        "conflicts": [c.to_dict() for c in plan.conflicts],
    }


def validate_plan_output(payload: dict[str, Any]) -> None:
    required = {"ok", "existing_count", "summary", "operations", "conflicts"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"plan output missing required keys: {', '.join(missing)}")
    if not isinstance(payload["ok"], bool):
        raise ValueError("plan output ok must be boolean")
    if not isinstance(payload["operations"], list) or not isinstance(payload["conflicts"], list):
        raise ValueError("plan output operations and conflicts must be arrays")


def compliance_artifacts(
    output_dir: str | Path,
    *,
    package_name: str,
    version: str,
    source_dir: str | Path = ".",
    dist_dir: str | Path | None = None,
) -> list[Path]:
    root = Path(output_dir)
    created_at = utc_now()
    source = Path(source_dir)
    dist = Path(dist_dir) if dist_dir is not None else source / "dist"
    dependencies = _installed_dependencies(package_name)
    subjects = _artifact_subjects(dist if dist.exists() else source, package_name=package_name)
    security = _security_scan(source)
    dependency = _dependency_audit(dependencies)
    artifacts = {
        "sbom.spdx.json": {
            "SPDXID": "SPDXRef-DOCUMENT",
            "spdxVersion": "SPDX-2.3",
            "name": package_name,
            "creationInfo": {"created": created_at, "creators": [f"Tool: {current_profile().name}"]},
            "packages": [
                {"SPDXID": f"SPDXRef-Package-{item['name']}", "name": item["name"], "versionInfo": item["version"]}
                for item in [{"name": package_name, "version": version}, *dependencies]
            ],
        },
        "provenance.intoto.json": {
            "_type": "https://in-toto.io/Statement/v1",
            "subject": subjects,
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {
                "buildType": f"{current_profile().name}-local",
                "builder": {"id": os.getenv("GITHUB_SERVER_URL", "local")},
                "metadata": {"buildStartedOn": created_at},
                "invocation": {"configSource": {"uri": str(source.resolve())}},
            },
        },
        "security-scan.json": security | {"generated_at": created_at},
        "dependency-vulnerability.json": dependency | {"generated_at": created_at},
        "release-gates.json": {
            "ok": security["ok"] and dependency["ok"] and bool(subjects),
            "generated_at": created_at,
            "required_gates": ["ruff", "ruff-format", "yamllint", "pytest", "ssot-validate"],
            "artifact_subjects": len(subjects),
            "security_scan_ok": security["ok"],
            "dependency_vulnerability_ok": dependency["ok"],
        },
    }
    return [write_json(root / name, payload) for name, payload in artifacts.items()]


def validate_compliance_gate(artifact_dir: str | Path) -> dict[str, Any]:
    root = Path(artifact_dir)
    required = (
        "sbom.spdx.json",
        "provenance.intoto.json",
        "security-scan.json",
        "dependency-vulnerability.json",
        "release-gates.json",
    )
    missing = [name for name in required if not (root / name).is_file()]
    reports: dict[str, Any] = {}
    for name in required:
        path = root / name
        if path.is_file():
            reports[name] = json.loads(path.read_text(encoding="utf-8"))
    failures = list(missing)
    for name in ("security-scan.json", "dependency-vulnerability.json", "release-gates.json"):
        report = reports.get(name)
        if isinstance(report, dict) and report.get("ok") is not True:
            failures.append(f"{name} not ok")
    sbom = reports.get("sbom.spdx.json", {})
    if isinstance(sbom, dict) and not sbom.get("packages"):
        failures.append("sbom.spdx.json has no packages")
    provenance = reports.get("provenance.intoto.json", {})
    if isinstance(provenance, dict) and not provenance.get("subject"):
        failures.append("provenance.intoto.json has no subjects")
    return {"ok": not failures, "missing": missing, "failures": failures, "reports": sorted(reports)}


def _installed_dependencies(package_name: str) -> list[dict[str, str]]:
    names = {"PyYAML", "requests"}
    out: list[dict[str, str]] = []
    for name in sorted(names):
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            version = "not-installed"
        out.append({"name": name, "version": version})
    return out


def _artifact_subjects(root: Path, *, package_name: str) -> list[dict[str, Any]]:
    files = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
    subjects: list[dict[str, Any]] = []
    for path in files:
        if any(
            part in {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
            for part in path.parts
        ):
            continue
        if len(subjects) >= 200:
            break
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        subjects.append({"name": f"{package_name}:{path.as_posix()}", "digest": {"sha256": digest}})
    return subjects


def _security_scan(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in sorted((root / "packages" / current_profile().name / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name in {"eval", "exec", "pickle.loads", "pickle.load"}:
                    findings.append({"path": str(path), "line": node.lineno, "rule": f"forbidden-call:{name}"})
                if name in {"subprocess.run", "subprocess.Popen", "subprocess.call"}:
                    if any(
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in node.keywords
                    ):
                        findings.append({"path": str(path), "line": node.lineno, "rule": "subprocess-shell-true"})
    return {"ok": not findings, "scanner": f"{current_profile().name}-ast-security-scan", "findings": findings}


def _dependency_audit(dependencies: list[dict[str, str]]) -> dict[str, Any]:
    denied = {("requests", "2.19.0"), ("pyyaml", "5.3.0")}
    findings = [
        {"name": item["name"], "version": item["version"], "advisory": "local-denylist"}
        for item in dependencies
        if (item["name"].lower(), item["version"]) in denied
    ]
    return {
        "ok": not findings,
        "scanner": f"{current_profile().name}-lock-dependency-audit",
        "dependencies": dependencies,
        "findings": findings,
    }


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_name(func.value)
        return f"{base}.{func.attr}" if base else func.attr
    return ""
