from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from wyrmctl.artifacts import PlanArtifact, write_artifact
from wyrmctl.cli import _apply_plan_artifact, _write_plan_artifact, main
from wyrmctl.contracts import semantic_digest
from wyrmctl.models import DesiredState, ExistingState
from wyrmctl.planner import Plan
from wyrmctl.profile import NPMCTL_PROFILE
from wyrmctl.repository import repository_document
from wyrmctl.schema import Capabilities


def test_versioned_cli_commands(tmp_path: Path, capsys) -> None:
    assert main(["--output", "json", "version"]) == 0
    assert json.loads(capsys.readouterr().out)["contracts"]["DesiredState"]["current"] == 3
    assert main(["--output", "json", "version"], profile=NPMCTL_PROFILE) == 0
    assert main(["--output", "json", "version"], profile=NPMCTL_PROFILE) == 0
    assert main(["--output", "json", "contract", "list"]) == 0
    assert main(["--output", "json", "contract", "show", "DesiredState"]) == 0

    artifact = PlanArtifact("id", "org/repo", "prod", "abc", "desired", "live", ())
    artifact_path = write_artifact(tmp_path / "plan.yaml", artifact.to_dict())
    assert main(["--output", "json", "contract", "check", str(artifact_path)]) == 0
    assert main(["--output", "json", "artifact", "inspect", str(artifact_path)]) == 0
    assert main(["--output", "json", "artifact", "digest", str(artifact_path)]) == 0

    directory = tmp_path / ".wyrmctl"
    directory.mkdir()
    (directory / "prod.yaml").write_text("x: 1", encoding="utf-8")
    repository_path = directory / "repository.yaml"
    repository_path.write_text(
        yaml.safe_dump(
            repository_document(
                "repo",
                owners=["owner"],
                environments={"production": {"main": "prod.yaml"}},
                domains=[],
            )
        ),
        encoding="utf-8",
    )
    assert main(["--output", "json", "repo", "validate", str(repository_path)]) == 0
    assert (
        main(
            [
                "--output",
                "json",
                "repo",
                "status",
                str(repository_path),
                "--environment",
                "production",
            ]
        )
        == 0
    )
    lock = {
        "apiVersion": "wyrmctl.com/v1",
        "kind": "NpmctlLock",
        "schemaVersion": 1,
        "metadata": {},
        "spec": {},
    }
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text(yaml.safe_dump(lock), encoding="utf-8")
    second.write_text(yaml.safe_dump(lock), encoding="utf-8")
    assert main(["--output", "json", "lock", "check", str(first), str(second)]) == 0
    lock["spec"]["changed"] = True
    second.write_text(yaml.safe_dump(lock), encoding="utf-8")
    assert main(["--output", "json", "lock", "check", str(first), str(second)]) == 1


class FakeClient:
    def __init__(self, **_kwargs) -> None:
        pass

    def capabilities(self) -> Capabilities:
        return Capabilities.full_for_tests()

    def existing_state(self, **_kwargs) -> ExistingState:
        return ExistingState()


def test_write_and_apply_empty_plan_artifact(tmp_path: Path, capsys, monkeypatch) -> None:
    capabilities = Capabilities.full_for_tests()
    plan = Plan((), (), 0)
    out = tmp_path / "generated.yaml"
    args = argparse.Namespace(
        command="plan",
        prune_owned=False,
        repository="org/repo",
        environment="prod",
        commit="abc",
        expires_at=None,
        artifact_out=str(out),
    )
    _write_plan_artifact(args, plan, DesiredState(schema_version=3), ExistingState(), capabilities)
    assert out.exists()
    document = yaml.safe_load(out.read_text(encoding="utf-8"))
    document["spec"]["inputs"]["liveStateFingerprint"] = semantic_digest([])
    write_artifact(out, document)
    apply_args = argparse.Namespace(
        artifact=str(out),
        repository="org/repo",
        environment="prod",
        commit="abc",
        output="json",
    )
    assert _apply_plan_artifact(apply_args, FakeClient()) == 0
    assert json.loads(capsys.readouterr().out)["result"]["applied"] is True
    args.prune_owned = True
    import pytest
    from wyrmctl.errors import ValidationError

    with pytest.raises(ValidationError, match="prune"):
        _write_plan_artifact(args, plan, DesiredState(), ExistingState(), capabilities)
    args.prune_owned = False
    with pytest.raises(ValidationError, match="does not yet support DNS"):
        _write_plan_artifact(
            args,
            plan,
            SimpleNamespace(dns_records=(object(),)),
            ExistingState(),
            capabilities,
        )

    import wyrmctl.cli as cli

    monkeypatch.setattr(cli, "NpmClient", FakeClient)
    desired = tmp_path / "desired.yaml"
    desired.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "wyrmctl.com/v1",
                "kind": "DesiredState",
                "schemaVersion": 3,
                "metadata": {},
                "spec": {},
            }
        ),
        encoding="utf-8",
    )
    common = ["--base-url", "http://npm", "--identity", "user", "--secret", "secret", "--output", "json"]
    assert main(common + ["apply", str(desired), "--artifact", str(out)]) == 2
    assert main(common + ["apply"]) == 2
    generated = tmp_path / "cli-plan.yaml"
    assert (
        main(
            common
            + [
                "plan",
                str(desired),
                "--artifact-out",
                str(generated),
                "--repository",
                "org/repo",
                "--environment",
                "prod",
                "--commit",
                "abc",
            ]
        )
        == 0
    )
    assert generated.exists()
    assert (
        main(
            common
            + ["apply", "--artifact", str(out), "--repository", "org/repo", "--environment", "prod", "--commit", "abc"]
        )
        == 0
    )
