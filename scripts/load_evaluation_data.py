"""Explicit operator command that loads the synthetic evaluation corpus.

Run only through `make load-evaluation-data`. Nothing starts this script
automatically. Production refuses it before any database or upload-storage
object is constructed, and every record is mapped through the existing case,
document, workflow, and audit services with the deterministic fake provider.
See `specs/004-environment-data-seeding/contracts/evaluation-loader.md`.
"""

import asyncio
import hashlib
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UNDERWRITEFLOW_SRC", "/app/src"))

from fastapi import UploadFile  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from starlette.datastructures import Headers  # noqa: E402

from underwriteflow.audit.events import version_details  # noqa: E402
from underwriteflow.cases.schemas import CaseCreate  # noqa: E402
from underwriteflow.cases.service import CaseService  # noqa: E402
from underwriteflow.cases.submission import SubmissionService  # noqa: E402
from underwriteflow.config import Settings, get_settings  # noqa: E402
from underwriteflow.database import Database  # noqa: E402
from underwriteflow.evaluation.dataset import (  # noqa: E402
    DatasetPreflightError,
    dataset_sha256,
    load_configuration_manifest,
    load_dataset,
    preflight_dataset,
)
from underwriteflow.persistence.models import (  # noqa: E402
    Case,
    ProductVersion,
    RulebookVersion,
    User,
)
from underwriteflow.providers.fake import FakeProvider  # noqa: E402
from underwriteflow.storage import UploadStorage  # noqa: E402

from evaluation_records import (  # noqa: E402
    RecordCollision,
    rendered_document,
    stored_documents,
    verify_case,
    verify_document,
    verify_document_set,
    verify_result,
    verify_route,
)
from loader_audit import (  # noqa: E402
    ACTOR_TOKEN_ENV,
    append_marker,
    resolve_actor,
    verify_baseline_versions,
)

# Only the deterministic local provider may ever run during a load.
PROVIDER_FACTORY = FakeProvider

APPLICANT_EMAIL = "applicant@synthetic.test"
KEY_PREFIX = "evaluation"
RECORD_EVENT = "evaluation_record_loaded"
DATASET_EVENT = "evaluation_dataset_loaded"

ERROR_FORBIDDEN = "evaluation_load_forbidden"
ERROR_COLLISION = "evaluation_record_collision"
ERROR_PRECONDITION = "evaluation_load_precondition_failed"
ERROR_PREFLIGHT = "evaluation_load_preflight_failed"
ERROR_UNEXPECTED = "evaluation_load_failed"


# Build the reserved idempotency key for one source record.
def record_key(dataset_sha256_value: str, source_case_id: str) -> str:
    return f"{KEY_PREFIX}:{dataset_sha256_value}:{source_case_id}"


# Order records so every run walks the corpus in the same sequence.
def ordered_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda record: record["case_id"])


# Identify an injected record subset by its canonical serialized bytes.
def records_sha256(records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        ordered_records(records), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


# Build the safe completion object one successful load prints.
def success_result(
    environment: str,
    dataset_sha256: str,
    expected_count: int,
    created_count: int,
    resumed_count: int,
    verified_count: int,
) -> dict[str, Any]:
    return {
        "environment": environment,
        "dataset_sha256": dataset_sha256,
        "expected_count": expected_count,
        "created_count": created_count,
        "resumed_count": resumed_count,
        "verified_count": verified_count,
        "complete": verified_count == expected_count,
    }


# Build the safe failure object a refused or incomplete load prints.
def failure_result(
    environment: str,
    error_code: str,
    dataset_sha256: str | None = None,
    source_case_id: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "environment": environment,
        "complete": False,
        "error_code": error_code,
    }
    for key, value in (
        ("dataset_sha256", dataset_sha256),
        ("source_case_id", source_case_id),
        ("stage", stage),
    ):
        if value is not None:
            result[key] = value
    return result


# Upload one rendered synthetic document through the existing case service.
async def upload_document(
    session: AsyncSession,
    service: CaseService,
    case: Case,
    actor_id: Any,
    document_code: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> None:
    upload = UploadFile(
        file=BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )
    await service.add_document(
        session, case, upload, document_code, actor_id
    )


# Load or verify one source record and report how it was satisfied.
async def load_record(
    session: AsyncSession,
    settings: Settings,
    service: CaseService,
    record: dict[str, Any],
    identity: str,
    applicant_id: Any,
    actor_id: Any,
    configuration: Any,
) -> str:
    key = record_key(identity, record["case_id"])
    case = await session.scalar(
        select(Case).where(
            Case.applicant_user_id == applicant_id,
            Case.idempotency_key == key,
        )
    )
    created = case is None
    if created:
        case = await service.create_case(
            session,
            applicant_id,
            CaseCreate(
                product_code=record["product_code"],
                idempotency_key=key,
                journey=record["journey_type"],
                payload=record["workflow_input"]["payload"],
                document_codes=[
                    document["document_id"]
                    for document in record["documents"]
                ],
            ),
            version=record["configuration_version"],
        )
    else:
        await verify_case(session, case, record)

    existing = await stored_documents(session, case, record)
    verify_document_set(record, existing)
    for document in sorted(
        record["documents"], key=lambda item: item["document_id"]
    ):
        code = document["document_id"]
        filename, content, content_type, content_hash = rendered_document(
            document, configuration
        )
        if code in existing:
            verify_document(record, existing[code], content_hash)
            continue
        await upload_document(
            session,
            service,
            case,
            applicant_id,
            code,
            filename,
            content,
            content_type,
        )

    if case.status == "new":
        result = await SubmissionService(
            PROVIDER_FACTORY(),
            settings.upload_root,
            settings.database_url,
            retry_count=0,
        ).submit(session, case, applicant_id)
        recommendation = result.get("recommendation") or {}
        verify_route(record, str(recommendation.get("route", "")))
    await verify_result(session, case, record)

    product_version = await session.get(
        ProductVersion, case.product_version_id
    )
    rulebook_version = await session.get(
        RulebookVersion, case.rulebook_version_id
    )
    await append_marker(
        session,
        RECORD_EVENT,
        {
            "dataset_sha256": identity,
            "source_case_id": record["case_id"],
            "split": record["split"],
            "fixture_label": record["fixture_label"],
            "product_version": record["configuration_version"],
            "product_code": record["product_code"],
            **version_details(product_version, rulebook_version),
        },
        actor_id,
        case_id=case.id,
    )
    return "created" if created else "resumed"


# Load the authoritative corpus, or an injected subset, exactly once.
async def load_evaluation_data(
    settings: Settings | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active = settings or get_settings()
    if not active.evaluation_loading_allowed:
        return failure_result(active.environment_mode, ERROR_FORBIDDEN)

    injected = records is not None
    corpus = records if injected else load_dataset()
    configurations = load_configuration_manifest()
    if not injected:
        preflight_dataset(corpus, configurations)
    identity = records_sha256(corpus) if injected else dataset_sha256()
    if os.getenv("LANGSMITH_TRACING", "false").casefold() == "true":
        return failure_result(
            active.environment_mode, ERROR_PRECONDITION, identity
        )

    database = Database(active.database_url)
    storage = UploadStorage(Path(active.upload_root))
    service = CaseService(storage)
    created_count = 0
    resumed_count = 0
    verified_count = 0
    try:
        async with database.session_factory() as session:
            applicant = await session.scalar(
                select(User).where(
                    User.email == APPLICANT_EMAIL, User.is_active.is_(True)
                )
            )
            if applicant is None:
                return failure_result(
                    active.environment_mode, ERROR_PRECONDITION, identity
                )
            actor = await resolve_actor(session, active)
            if actor is None:
                return failure_result(
                    active.environment_mode, ERROR_PRECONDITION, identity
                )
            if not await verify_baseline_versions(session, corpus):
                return failure_result(
                    active.environment_mode, ERROR_PRECONDITION, identity
                )
            for record in ordered_records(corpus):
                configuration = configurations[
                    (record["product_code"], record["configuration_version"])
                ]
                try:
                    outcome = await load_record(
                        session,
                        active,
                        service,
                        record,
                        identity,
                        applicant.id,
                        actor.id,
                        configuration,
                    )
                except RecordCollision as collision:
                    return failure_result(
                        active.environment_mode,
                        ERROR_COLLISION,
                        identity,
                        collision.source_case_id,
                        collision.stage,
                    )
                created_count += outcome == "created"
                resumed_count += outcome == "resumed"
                verified_count += 1
            if verified_count == len(corpus):
                await append_marker(
                    session,
                    DATASET_EVENT,
                    {
                        "dataset_sha256": identity,
                        "environment_mode": active.environment_mode,
                        "expected_case_count": len(corpus),
                        "verified_case_count": verified_count,
                    },
                    actor.id,
                )
    finally:
        await database.close()

    return success_result(
        active.environment_mode,
        identity,
        len(corpus),
        created_count,
        resumed_count,
        verified_count,
    )


# Run the explicit load and exit with its completion status. Every failure,
# expected or not, surfaces as one sanitized JSON object: no traceback, no
# internal detail, ever reaches standard output or standard error.
def main() -> int:
    try:
        result = asyncio.run(load_evaluation_data())
    except DatasetPreflightError as error:
        result = failure_result(
            get_settings().environment_mode,
            ERROR_PREFLIGHT,
            source_case_id=error.case_id,
            stage=error.stage,
        )
    except Exception:
        result = failure_result(
            get_settings().environment_mode, ERROR_UNEXPECTED
        )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("complete") else 1


if __name__ == "__main__":
    sys.exit(main())
