"""Contract registry command handlers."""

from typing import Any

from wyrmctl.contracts import BUILTIN_CONTRACTS, check_document
from wyrmctl.output import command_result


def contract_list() -> dict[str, Any]:
    return command_result(ok=True, code="CONTRACTS_LISTED", data={"contracts": BUILTIN_CONTRACTS.matrix()})


def contract_show(kind: str) -> dict[str, Any]:
    return command_result(ok=True, code="CONTRACT_SHOWN", data=BUILTIN_CONTRACTS.support(kind).to_dict())


def contract_check(document: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    warnings = check_document(document, BUILTIN_CONTRACTS, strict=strict)
    return command_result(
        ok=True,
        code="CONTRACT_COMPATIBLE",
        data={"kind": document["kind"], "schemaVersion": document["schemaVersion"], "warnings": warnings},
    )
