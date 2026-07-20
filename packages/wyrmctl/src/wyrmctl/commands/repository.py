"""Repository manifest command handlers."""

from typing import Any

from wyrmctl.output import command_result
from wyrmctl.repository import load_repository


def repository_validate(path: str) -> dict[str, Any]:
    repository = load_repository(path)
    return command_result(
        ok=True,
        code="REPOSITORY_VALID",
        data={
            "name": repository.name,
            "digest": repository.digest,
            "owners": list(repository.owners),
            "environments": sorted(repository.environments),
            "domains": list(repository.domains),
        },
    )


def repository_status(path: str, environment: str) -> dict[str, Any]:
    repository = load_repository(path)
    selected = repository.environment(environment)
    return command_result(
        ok=True,
        code="REPOSITORY_STATUS",
        data={
            "name": repository.name,
            "environment": selected.name,
            "desiredState": {key: str(value) for key, value in sorted(selected.desired_state.items())},
        },
    )
