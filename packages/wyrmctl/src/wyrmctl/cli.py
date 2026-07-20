"""Command-line interface for wyrmctl."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Sequence

from wyrmctl import __version__
from wyrmctl.config import apply_config, load_config
from wyrmctl.diagnostics import doctor_report, environment_report
from wyrmctl.errors import (
    ApiError,
    CapabilityError,
    CertificateApiError,
    CertificateSafetyError,
    ConflictError,
    MigrationError,
    NpmctlError,
    ValidationError,
)
from wyrmctl.models import ResourceKind
from wyrmctl.output import format_plan_text, write_error, write_output
from wyrmctl.profile import ToolProfile, current_profile, use_profile

EXIT_OK = 0
EXIT_CONFLICT = 1
EXIT_USAGE_OR_VALIDATION = 2
EXIT_API = 3
EXIT_CAPABILITY = 4

NpmClient: Any | None = None
_PLUGIN_REGISTRY_IMPL: Any | None = None


class PluginRegistry:
    """Lazy plugin registry proxy for CLI patch points."""

    @staticmethod
    def discover() -> Any:
        return _plugin_registry_cls().discover()


def load_desired_state(*args: Any, **kwargs: Any) -> Any:
    """Lazy desired-state loader wrapper for CLI patch points."""

    from wyrmctl.loader import load_desired_state as _load_desired_state

    return _load_desired_state(*args, **kwargs)


def validate_plan_output(*args: Any, **kwargs: Any) -> Any:
    """Lazy plan-output validator wrapper for CLI patch points."""

    from wyrmctl.operational import validate_plan_output as _validate_plan_output

    return _validate_plan_output(*args, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(
        prog=current_profile().name,
        description="Owner-scoped plan/apply/adopt controller for Nginx Proxy Manager resources.",
    )
    parser.add_argument("--version", action="version", version=f"{current_profile().name} {__version__}")
    parser.add_argument("--config", help=f"TOML config file with [{current_profile().config_section}] settings")
    parser.add_argument("--base-url", default=os.getenv("NPM_BASE_URL"), help="NPM API URL, e.g. http://host:81/api")
    parser.add_argument("--identity", default=os.getenv("NPM_IDENTITY"), help="NPM login identity")
    parser.add_argument("--secret", default=os.getenv("NPM_SECRET"), help="NPM login secret")
    parser.add_argument(
        "--timeout",
        default=float(os.getenv("NPM_TIMEOUT_S")) if os.getenv("NPM_TIMEOUT_S") else None,
        type=float,
        help="HTTP timeout seconds",
    )
    parser.add_argument("--output", choices=("text", "json"), default="text", help="Output format")

    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate desired state")
    validate.add_argument("desired_state")

    migrate = sub.add_parser("migrate", help="Migrate desired-state schema")
    migrate.add_argument("path")
    migrate.add_argument("--write", action="store_true", help="Write migrated files")
    migrate.add_argument("--check", action="store_true", help="Fail if migration is needed")

    health = sub.add_parser("health", help="Call NPM API health endpoint")
    health.set_defaults(needs_api=True)

    doctor = sub.add_parser("doctor", help="Diagnose config, API reachability, and capabilities")
    doctor.set_defaults(needs_api=False)

    env = sub.add_parser("env", help=f"Show redacted {current_profile().name} environment diagnostics")
    env.set_defaults(needs_api=False)

    version = sub.add_parser("version", help="Show machine-readable version metadata")
    version.add_argument("--json", action="store_true", help="Emit JSON version metadata")

    contract = sub.add_parser("contract", help="Inspect versioned document contracts")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    contract_sub.add_parser("list", help="List built-in contract compatibility")
    contract_show = contract_sub.add_parser("show", help="Show one contract")
    contract_show.add_argument("kind")
    contract_check = contract_sub.add_parser("check", help="Check a document contract")
    contract_check.add_argument("path")
    contract_check.add_argument("--strict", action="store_true")

    repo = sub.add_parser("repo", help=f"Inspect a {current_profile().name} repository manifest")
    repo_sub = repo.add_subparsers(dest="repo_command", required=True)
    repo_validate = repo_sub.add_parser("validate", help="Validate a repository manifest")
    repo_validate.add_argument("path")
    repo_status = repo_sub.add_parser("status", help="Resolve one repository environment")
    repo_status.add_argument("path")
    repo_status.add_argument("--environment", required=True)

    lock = sub.add_parser("lock", help="Check reproducibility lockfiles")
    lock_sub = lock.add_subparsers(dest="lock_command", required=True)
    lock_check = lock_sub.add_parser("check", help="Compare expected and actual lockfiles")
    lock_check.add_argument("expected")
    lock_check.add_argument("actual")

    artifact = sub.add_parser("artifact", help="Inspect immutable execution artifacts")
    artifact_sub = artifact.add_subparsers(dest="artifact_command", required=True)
    artifact_inspect = artifact_sub.add_parser("inspect", help="Validate and summarize an artifact")
    artifact_inspect.add_argument("path")
    artifact_inspect.add_argument("--strict", action="store_true")
    artifact_digest = artifact_sub.add_parser("digest", help="Print an artifact semantic digest")
    artifact_digest.add_argument("path")

    completion = sub.add_parser("completion", help="Generate shell completion script")
    completion.add_argument("shell", choices=("bash", "powershell", "zsh"))

    schema = sub.add_parser("schema", help="OpenAPI schema commands")
    schema_sub = schema.add_subparsers(dest="schema_command", required=True)
    fetch = schema_sub.add_parser("fetch", help="Fetch /schema from NPM")
    fetch.add_argument("--write", help="Write schema JSON to path")
    fetch.set_defaults(needs_api=True)
    caps = schema_sub.add_parser("capabilities", help="Show detected endpoint capabilities")
    caps.add_argument("--schema", help="Schema JSON path; fetches from NPM when omitted")
    caps.set_defaults(needs_api_optional_schema=True)
    check = schema_sub.add_parser("check", help="Validate required endpoint capabilities")
    check.add_argument("--schema", help="Schema JSON path; fetches from NPM when omitted")
    check.set_defaults(needs_api_optional_schema=True)

    plan = sub.add_parser("plan", help="Compute owner-scoped CRUD plan")
    _add_reconcile_args(plan)
    plan.add_argument("--artifact-out", help="Write an immutable PlanArtifact")
    _add_artifact_binding_args(plan)
    plan.add_argument("--validate-output", action="store_true", help="Validate plan output against wyrmctl schema")
    plan.set_defaults(needs_api=True)

    apply = sub.add_parser("apply", help="Apply a clean owner-scoped CRUD plan")
    _add_reconcile_args(apply, desired_required=False)
    apply.add_argument("--artifact", help="Apply an exact reviewed PlanArtifact")
    _add_artifact_binding_args(apply)
    apply.add_argument("--dry-run", action="store_true", help="Plan but do not mutate NPM")
    apply.add_argument("--backup-dir", help="Write remote state backup before apply")
    apply.add_argument("--report", help="Write structured apply transaction report")
    apply.add_argument("--rollback-plan", help="Write best-effort rollback plan")
    apply.add_argument("--audit-log", dest="audit_log_path", help="Write local audit log JSON for this apply")
    apply.add_argument("--validate-output", action="store_true", help="Validate plan output against wyrmctl schema")
    apply.set_defaults(needs_api=True)

    adopt = sub.add_parser("adopt", help="Adopt unmanaged matching resources by writing metadata")
    _add_reconcile_args(adopt)
    adopt.add_argument("--allow-field-drift", action="store_true", help="Allow adopting resources whose fields differ")
    adopt.add_argument("--force", action="store_true", help="Alias for --allow-field-drift with explicit intent")
    adopt.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only attach ownership metadata to compatible unmanaged resources; never create adjacent resources",
    )
    adopt.add_argument("--validate-output", action="store_true", help="Validate plan output against wyrmctl schema")
    adopt.set_defaults(needs_api=True, adopt=True)

    drift = sub.add_parser("drift", help="Report remote drift without applying mutations")
    _add_reconcile_args(drift)
    drift.set_defaults(needs_api=True)

    audit = sub.add_parser("audit-log", help="Read NPM audit log entries")
    audit.add_argument("--since", help="Optional since filter passed to NPM")
    audit.set_defaults(needs_api=True)

    compliance = sub.add_parser("compliance", help="Compliance artifact commands")
    compliance_sub = compliance.add_subparsers(dest="compliance_command", required=True)
    artifacts = compliance_sub.add_parser(
        "artifacts", help="Generate SBOM, provenance, scan, and release-gate artifacts"
    )
    artifacts.add_argument("--output-dir", required=True)
    artifacts.add_argument("--source-dir", default=".")
    artifacts.add_argument("--dist-dir")
    gate = compliance_sub.add_parser("gate", help="Validate generated compliance artifacts")
    gate.add_argument("--artifact-dir", required=True)

    plugins = sub.add_parser("plugins", help="Inspect runtime plugin discovery")
    plugins_sub = plugins.add_subparsers(dest="plugins_command", required=True)
    plugins_sub.add_parser("list", help="List discovered plugin providers")

    dns = sub.add_parser("dns", help="Inspect DNS extension providers")
    dns_sub = dns.add_subparsers(dest="dns_command", required=True)
    dns_sub.add_parser("providers", help="List discovered DNS providers")
    dns_doctor = dns_sub.add_parser("doctor", help="Validate one DNS provider can be loaded")
    dns_doctor.add_argument("--provider", required=True)
    dns_zones = dns_sub.add_parser("zones", help="List zones for a DNS provider")
    dns_zones.add_argument("--provider", required=True)
    dns_records = dns_sub.add_parser("records", help="List records for a DNS provider zone")
    dns_records.add_argument("--provider", required=True)
    dns_records.add_argument("--zone", required=True)

    return parser


def _add_reconcile_args(parser: argparse.ArgumentParser, *, desired_required: bool = True) -> None:
    parser.add_argument("desired_state", nargs=None if desired_required else "?")
    parser.add_argument("--owner", help="Limit operation to one owner scope")
    parser.add_argument("--no-updates", action="store_true", help="Conflict on owned drift instead of updating")
    parser.add_argument("--prune-owned", action="store_true", help="Delete owned resources absent from desired state")
    parser.add_argument(
        "--certificate-mode",
        choices=("reuse", "create", "rotate"),
        default="create",
        help="Certificate mutation policy during reconcile",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=(
            "proxy_hosts",
            "certificates",
            "access_lists",
            "redirection_hosts",
            "dead_hosts",
            "streams",
            "users",
            "settings",
        ),
        help="Limit reconcile to one resource family; may be repeated",
    )


def _add_artifact_binding_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--environment", default="production")
    parser.add_argument("--commit", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--expires-at")


def main(argv: Sequence[str] | None = None, *, profile: ToolProfile | None = None) -> int:
    if profile is not None:
        with use_profile(profile):
            return _main_impl(argv)
    return _main_impl(argv)


def _main_impl(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        apply_config(args, load_config(getattr(args, "config", None)))
        return _dispatch(args, parser)
    except ValidationError as exc:
        write_error(args.output, "validation_error", str(exc))
        return EXIT_USAGE_OR_VALIDATION
    except MigrationError as exc:
        write_error(args.output, "migration_error", str(exc))
        return EXIT_USAGE_OR_VALIDATION
    except CertificateSafetyError as exc:
        write_error(args.output, exc.code, str(exc), suggested_action=exc.suggested_action, details=exc.details)
        return EXIT_CONFLICT
    except ConflictError as exc:
        write_error(args.output, "conflict_error", str(exc))
        return EXIT_CONFLICT
    except CapabilityError as exc:
        write_error(args.output, "capability_error", _redact_cli_message(str(exc), args))
        return EXIT_CAPABILITY
    except CertificateApiError as exc:
        write_error(
            args.output,
            exc.code,
            _redact_cli_message(str(exc), args),
            retryable=exc.retryable,
            suggested_action=exc.suggested_action,
            details=exc.details,
        )
        return EXIT_API
    except ApiError as exc:
        write_error(args.output, "api_error", _redact_cli_message(str(exc), args))
        return EXIT_API
    except NpmctlError as exc:
        write_error(args.output, f"{current_profile().name}_error", str(exc))
        return EXIT_USAGE_OR_VALIDATION


def _dispatch(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.command == "validate":
        desired = load_desired_state(args.desired_state)
        payload = _desired_summary(desired)
        write_output(args.output, payload, _format_validate_text(payload))
        return EXIT_OK

    if args.command == "env":
        payload = {"ok": True, "environment": environment_report(dict(os.environ))}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "version":
        from wyrmctl.contracts import BUILTIN_CONTRACTS

        payload = {
            "package": current_profile().name,
            "version": __version__,
            "schema_version": 3,
            "api_profile": "npm-2.10.4",
            "contracts": BUILTIN_CONTRACTS.matrix(),
        }
        text = json.dumps(payload, indent=2, sort_keys=True) if args.json or args.output == "json" else __version__
        write_output("json" if args.json else args.output, payload, text)
        return EXIT_OK

    if args.command == "contract":
        from wyrmctl.artifacts import read_artifact
        from wyrmctl.commands.contracts import contract_check, contract_list, contract_show

        if args.contract_command == "list":
            payload = contract_list()
        elif args.contract_command == "show":
            payload = contract_show(args.kind)
        else:
            payload = contract_check(read_artifact(args.path), strict=args.strict)
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "repo":
        from wyrmctl.commands.repository import repository_status, repository_validate

        payload = (
            repository_validate(args.path)
            if args.repo_command == "validate"
            else repository_status(args.path, args.environment)
        )
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "lock":
        from wyrmctl.commands.lock import lock_check

        payload = lock_check(args.expected, args.actual)
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK if payload["ok"] else EXIT_CONFLICT

    if args.command == "artifact":
        from wyrmctl.commands.artifacts import artifact_digest_command, artifact_inspect_command

        payload = (
            artifact_inspect_command(args.path, strict=args.strict)
            if args.artifact_command == "inspect"
            else artifact_digest_command(args.path)
        )
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "completion":
        payload = {"ok": True, "shell": args.shell}
        write_output(args.output, payload, _completion_script(args.shell))
        return EXIT_OK

    if args.command == "compliance":
        from wyrmctl.operational import compliance_artifacts, validate_compliance_gate

        if args.compliance_command == "gate":
            payload = validate_compliance_gate(args.artifact_dir)
            write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
            return EXIT_OK if payload["ok"] else EXIT_USAGE_OR_VALIDATION
        paths = compliance_artifacts(
            args.output_dir,
            package_name="wyrmctl",
            version=__version__,
            source_dir=args.source_dir,
            dist_dir=args.dist_dir,
        )
        payload = {"ok": True, "artifacts": [str(path) for path in paths]}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "plugins":
        registry = PluginRegistry.discover()
        payload = {"ok": True, "plugins": registry.to_dict()}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "dns":
        return _dns_command(args)

    if args.command == "migrate":
        from wyrmctl.migrations import migrate_path

        if args.write and args.check:
            raise ValidationError("migrate --write and --check cannot be combined")
        results = migrate_path(args.path, write=args.write)
        changed = [result for result in results if result.changed]
        payload = {
            "ok": not bool(changed and args.check),
            "changed": len(changed),
            "files": [str(result.path) for result in changed],
            "written": bool(args.write),
        }
        write_output(args.output, payload, f"migrations needed: {len(changed)}\nwritten: {str(args.write).lower()}")
        return EXIT_USAGE_OR_VALIDATION if changed and args.check else EXIT_OK

    client = None
    if getattr(args, "needs_api", False) or (
        getattr(args, "needs_api_optional_schema", False) and not getattr(args, "schema", None)
    ):
        _require_api_args(args, parser)
        client = _npm_client_cls()(
            base_url=args.base_url, identity=args.identity, secret=args.secret, timeout_s=args.timeout or 15.0
        )

    if args.command == "doctor":
        health = None
        capabilities = None
        if args.base_url and args.identity and args.secret:
            client = _npm_client_cls()(
                base_url=args.base_url,
                identity=args.identity,
                secret=args.secret,
                timeout_s=args.timeout or 15.0,
            )
            health = client.health()
            capabilities = client.capabilities().to_dict()
        payload = doctor_report(args=args, health=health, capabilities=capabilities)
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK if payload["ok"] else EXIT_USAGE_OR_VALIDATION

    if args.command == "health":
        assert client is not None
        payload = client.health()
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command == "schema":
        return _schema_command(args, client)

    if args.command == "audit-log":
        assert client is not None
        payload = {"ok": True, "entries": client.audit_log(since=args.since)}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK

    if args.command in {"plan", "apply", "adopt", "drift"}:
        from wyrmctl.apply import ApplyEngine
        from wyrmctl.dns import apply_dns_plan, compute_dns_plan
        from wyrmctl.operational import (
            drift_report,
            rollback_plan,
            transaction_report,
            write_json,
            write_state_backup,
        )
        from wyrmctl.planner import PlannerOptions, compute_plan

        assert client is not None
        if args.command == "apply" and args.artifact:
            if args.desired_state:
                raise ValidationError("apply accepts either DESIRED_STATE or --artifact, not both")
            return _apply_plan_artifact(args, client)
        if args.command == "apply" and not args.desired_state:
            raise ValidationError("apply requires DESIRED_STATE or --artifact")
        desired = load_desired_state(args.desired_state)
        capabilities = client.capabilities()
        existing = client.existing_state(
            include_certificates=capabilities.certificates.list,
            include_access_lists=capabilities.access_lists.list,
        )
        dns_providers = PluginRegistry.discover().dns_providers if desired.dns_records else {}
        options = PlannerOptions(
            owner=args.owner,
            allow_updates=not args.no_updates,
            prune_owned=args.prune_owned,
            adopt=args.command == "adopt",
            strict_adopt=not (getattr(args, "allow_field_drift", False) or getattr(args, "force", False)),
            allow_field_drift=getattr(args, "allow_field_drift", False) or getattr(args, "force", False),
            metadata_only_adopt=getattr(args, "metadata_only", False),
            resource_kinds=_parse_resource_kinds(getattr(args, "only", None)),
            certificate_mode=_default_certificate_mode(args),
        )
        plan = compute_plan(desired=desired, existing=existing, capabilities=capabilities, options=options)
        dns_plan = compute_dns_plan(
            desired.dns_records,
            dns_providers,
            owner=args.owner,
            prune_owned=args.prune_owned,
        )
        if args.command == "drift":
            payload = drift_report(plan)
            payload["dns"] = dns_plan.to_dict()
            payload["ok"] = bool(payload["ok"] and dns_plan.ok)
            write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
            return EXIT_OK if payload["ok"] else EXIT_CONFLICT
        plan_payload = _combined_plan_payload(plan, dns_plan)
        if getattr(args, "validate_output", False):
            try:
                validate_plan_output(plan_payload)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
        if args.command == "plan" or getattr(args, "dry_run", False):
            if getattr(args, "artifact_out", None):
                _write_plan_artifact(args, plan, desired, existing, capabilities)
            write_output(args.output, plan_payload, _format_combined_plan_text(plan, dns_plan))
            return EXIT_OK if plan.ok and dns_plan.ok else EXIT_CONFLICT
        if not plan.ok or not dns_plan.ok:
            write_output(args.output, plan_payload, _format_combined_plan_text(plan, dns_plan))
            return EXIT_CONFLICT
        if getattr(args, "backup_dir", None):
            write_state_backup(args.backup_dir, existing)
        result = ApplyEngine(client=client, capabilities=capabilities, existing_state=existing).apply(plan)
        dns_result = apply_dns_plan(dns_plan, dns_providers)
        payload = transaction_report(plan, result, dns_plan=dns_plan, dns_apply_result=dns_result)
        if getattr(args, "report", None):
            write_json(args.report, payload)
        if getattr(args, "rollback_plan", None):
            write_json(args.rollback_plan, rollback_plan(plan))
        if getattr(args, "audit_log_path", None):
            write_json(args.audit_log_path, {"ok": True, "operation": "apply", "summary": payload["summary"]})
        text = (
            _format_combined_plan_text(plan, dns_plan)
            + f"\napplied: true\nmutations: {len(result.mutations)}\ndns mutations: {len(dns_result.mutations)}"
        )
        write_output(args.output, payload, text)
        return EXIT_OK

    parser.error(f"unsupported command: {args.command}")  # pragma: no cover - argparse exits
    return EXIT_USAGE_OR_VALIDATION  # pragma: no cover


def _write_plan_artifact(args: argparse.Namespace, plan: Any, desired: Any, existing: Any, capabilities: Any) -> None:
    from dataclasses import asdict

    from wyrmctl.artifacts import build_plan_artifact, write_artifact
    from wyrmctl.contracts import semantic_digest

    if args.command != "plan" or args.prune_owned:
        raise ValidationError("ordinary PlanArtifact output does not authorize prune/delete operations")
    if desired.dns_records:
        raise ValidationError("PlanArtifact apply does not yet support DNS operations; use ordinary plan/apply")
    repository = args.repository or Path.cwd().name
    artifact = build_plan_artifact(
        plan,
        artifact_id=semantic_digest(plan.to_dict())[:24],
        repository=repository,
        environment=args.environment,
        commit=args.commit or "working-tree",
        desired_state_digest=semantic_digest(asdict(desired)),
        live_state_fingerprint=semantic_digest([item.to_dict() for item in existing.resources()]),
        provider_capabilities={},
        api_profiles={"npm": capabilities.api_profile},
        expires_at=args.expires_at,
    )
    write_artifact(args.artifact_out, artifact.to_dict())


def _apply_plan_artifact(args: argparse.Namespace, client: Any) -> int:
    from wyrmctl.apply import ApplyEngine
    from wyrmctl.artifacts import plan_from_artifact, read_artifact, validate_plan_binding
    from wyrmctl.contracts import semantic_digest

    document = read_artifact(args.artifact, strict=True)
    metadata = document["metadata"]
    spec = document["spec"]
    plan = plan_from_artifact(document)
    capabilities = client.capabilities()
    existing = client.existing_state(
        include_certificates=capabilities.certificates.list,
        include_access_lists=capabilities.access_lists.list,
    )
    from wyrmctl.artifacts.models import PlanArtifact

    artifact = PlanArtifact(
        artifact_id=str(metadata["id"]),
        repository=str(metadata["repository"]),
        environment=str(metadata["environment"]),
        commit=str(spec["source"]["commit"]),
        desired_state_digest=str(spec["inputs"]["desiredStateDigest"]),
        live_state_fingerprint=str(spec["inputs"]["liveStateFingerprint"]),
        operations=tuple(spec["operations"]),
        conflicts=tuple(spec.get("conflicts", [])),
        provider_capabilities=dict(spec.get("providerCapabilities", {})),
        api_profiles=dict(spec.get("apiProfiles", {})),
        created_at=str(metadata["createdAt"]),
        expires_at=metadata.get("expiresAt"),
    )
    validate_plan_binding(
        artifact,
        repository=args.repository or artifact.repository,
        environment=args.environment,
        commit=args.commit or artifact.commit,
        desired_state_digest=artifact.desired_state_digest,
        live_state_fingerprint=semantic_digest([item.to_dict() for item in existing.resources()]),
        provider_capabilities={},
        api_profiles={"npm": capabilities.api_profile},
    )
    result = ApplyEngine(client=client, capabilities=capabilities, existing_state=existing).apply(plan)
    payload = {"ok": True, "artifact": artifact.digest, "result": result.to_dict()}
    write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
    return EXIT_OK


def _schema_command(args: argparse.Namespace, client: Any | None) -> int:
    from wyrmctl.schema import Capabilities, load_openapi_schema

    if args.schema_command == "fetch":
        assert client is not None
        payload = client.openapi_schema()
        if args.write:
            Path(args.write).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK
    schema_doc = load_openapi_schema(args.schema) if args.schema else client.openapi_schema()  # type: ignore[union-attr]
    capabilities = Capabilities.from_openapi(schema_doc)
    payload = capabilities.to_dict()
    if args.schema_command == "check":
        required = [
            capabilities.proxy_hosts.list,
            capabilities.proxy_hosts.create,
            capabilities.proxy_hosts.update,
            capabilities.proxy_hosts.delete,
        ]
        payload["ok"] = all(required)
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK if payload["ok"] else EXIT_CAPABILITY
    write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
    return EXIT_OK


def _dns_command(args: argparse.Namespace) -> int:
    registry = PluginRegistry.discover()
    if args.dns_command == "providers":
        payload = {"ok": True, "providers": sorted(registry.dns_providers)}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK
    provider = registry.dns_providers.get(args.provider)
    if provider is None:
        raise ValidationError(f"unknown DNS provider: {args.provider}")
    if args.dns_command == "doctor":
        payload = {"ok": True, "provider": args.provider}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK
    if args.dns_command == "zones":
        payload = {"ok": True, "provider": args.provider, "zones": list(provider.zones())}
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK
    if args.dns_command == "records":
        payload = {
            "ok": True,
            "provider": args.provider,
            "zone": args.zone,
            "records": list(provider.records(args.zone)),
        }
        write_output(args.output, payload, json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_OK
    raise ValidationError(f"unsupported dns command: {args.dns_command}")  # pragma: no cover - argparse prevents this.


def _combined_plan_payload(plan: Any, dns_plan: Any) -> dict[str, Any]:
    payload = plan.to_dict()
    dns_payload = dns_plan.to_dict()
    payload["dns"] = dns_payload
    payload["ok"] = bool(payload["ok"] and dns_plan.ok)
    payload["summary"] = dict(payload["summary"])
    payload["summary"]["dns"] = dns_payload["summary"]
    return payload


def _format_combined_plan_text(plan: Any, dns_plan: Any) -> str:
    lines = [format_plan_text(plan), "dns:"]
    dns_payload = dns_plan.to_dict()
    lines.append(f"  plan ok: {str(dns_plan.ok).lower()}")
    lines.append(f"  existing: {dns_payload['existing_count']}")
    for key, value in dns_payload["summary"].items():
        lines.append(f"  {key}: {value}")
    for operation in dns_plan.operations:
        lines.append(
            f"    {operation.action.value:<6} dns_record   "
            f"{operation.provider}/{operation.zone}/{operation.name}/{operation.type} {operation.reason}"
        )
        for field, values in operation.diff.items():
            lines.append(f"      ~ {field}: {values.get('actual')!r} -> {values.get('desired')!r}")
    for conflict in dns_plan.conflicts:
        lines.append(f"    ! {conflict.code}: {conflict.message}")
    return "\n".join(lines)


def _require_api_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not (args.base_url and args.identity and args.secret):
        parser.error("--base-url, --identity, and --secret are required, or set NPM_BASE_URL/NPM_IDENTITY/NPM_SECRET")


def _desired_summary(desired: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "schemaVersion": desired.schema_version,
        "proxy_hosts": len(desired.proxy_hosts),
        "certificates": len(desired.certificates),
        "access_lists": len(desired.access_lists),
        "redirection_hosts": len(desired.redirection_hosts),
        "dead_hosts": len(desired.dead_hosts),
        "streams": len(desired.streams),
        "users": len(desired.users),
        "settings": len(desired.settings),
        "dns_records": len(desired.dns_records),
        "source_files": list(desired.source_files),
    }


def _format_validate_text(payload: dict[str, Any]) -> str:
    return (
        "desired state valid\n"
        f"proxy hosts: {payload['proxy_hosts']}\n"
        f"certificates: {payload['certificates']}\n"
        f"access lists: {payload['access_lists']}\n"
        f"redirection hosts: {payload['redirection_hosts']}\n"
        f"dead hosts: {payload['dead_hosts']}\n"
        f"streams: {payload['streams']}\n"
        f"users: {payload['users']}\n"
        f"settings: {payload['settings']}\n"
        f"dns records: {payload['dns_records']}"
    )


def _redact_cli_message(message: str, args: argparse.Namespace) -> str:
    redacted = message
    for value in (getattr(args, "identity", None), getattr(args, "secret", None)):
        if value:
            redacted = redacted.replace(str(value), "***")
    return redacted


def _completion_script(shell: str) -> str:
    commands = (
        "validate migrate health doctor env version contract repo lock artifact completion schema plan apply adopt "
        "drift audit-log compliance plugins dns"
    )
    if shell == "powershell":
        return f"Register-ArgumentCompleter -Native -CommandName {current_profile().name} -ScriptBlock {{ param($wordToComplete) '{commands}'.Split(' ') | Where-Object {{ $_ -like \"$wordToComplete*\" }} }}\n"
    if shell == "zsh":
        return f"#compdef {current_profile().name}\n_arguments '1:command:({commands})'\n"
    return f'complete -W "{commands}" {current_profile().name}\n'


_RESOURCE_KIND_ALIASES: dict[str, ResourceKind] = {
    "proxy_hosts": ResourceKind.PROXY_HOST,
    "certificates": ResourceKind.CERTIFICATE,
    "access_lists": ResourceKind.ACCESS_LIST,
    "redirection_hosts": ResourceKind.REDIRECTION_HOST,
    "dead_hosts": ResourceKind.DEAD_HOST,
    "streams": ResourceKind.STREAM,
    "users": ResourceKind.USER,
    "settings": ResourceKind.SETTING,
}


def _parse_resource_kinds(values: Sequence[str] | None) -> frozenset[ResourceKind] | None:
    if not values:
        return None
    return frozenset(_RESOURCE_KIND_ALIASES[value] for value in values)


def _default_certificate_mode(args: argparse.Namespace) -> str:
    if args.command == "adopt" and getattr(args, "certificate_mode", None) == "create":
        return "reuse"
    return getattr(args, "certificate_mode", "create")


def _npm_client_cls() -> Any:
    global NpmClient
    if NpmClient is None:
        from wyrmctl.client import NpmClient as _NpmClient

        NpmClient = _NpmClient
    return NpmClient


def _plugin_registry_cls() -> Any:
    global _PLUGIN_REGISTRY_IMPL
    if _PLUGIN_REGISTRY_IMPL is None:
        from wyrmctl.plugins import PluginRegistry as _PluginRegistry

        _PLUGIN_REGISTRY_IMPL = _PluginRegistry
    return _PLUGIN_REGISTRY_IMPL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
