"""Unit coverage for the explicit evaluation data loader.

`scripts/load_evaluation_data.py` is not part of the API package, so it is
reached by path the same way the end-to-end runner is. These tests touch no
database and no upload volume: they pin the dataset identity, the stable
reserved keys, the deterministic order, the sanitized output shape, and the
deterministic-provider rule.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

loader = pytest.importorskip("load_evaluation_data")

from underwriteflow.config import Settings  # noqa: E402
from underwriteflow.evaluation.dataset import dataset_sha256  # noqa: E402
from underwriteflow.providers.fake import FakeProvider  # noqa: E402

SAFE_SUCCESS_KEYS = {
    "environment",
    "dataset_sha256",
    "expected_count",
    "created_count",
    "resumed_count",
    "verified_count",
    "complete",
}
SAFE_FAILURE_KEYS = SAFE_SUCCESS_KEYS | {
    "error_code",
    "source_case_id",
    "stage",
}


# Given the shipped corpus, when hashed, then a stable hex identity is used.
def test_dataset_identity_is_a_stable_sha256() -> None:
    identity = dataset_sha256()

    assert len(identity) == 64
    assert identity == identity.lower()
    assert identity == dataset_sha256()


# Given a dataset hash and source case, when keyed, then the reserved key
# is the documented namespaced value.
def test_record_key_is_namespaced_by_dataset_and_case() -> None:
    key = loader.record_key("a" * 64, "motor-private-car-001")

    assert key == f"evaluation:{'a' * 64}:motor-private-car-001"


# Given the same inputs, when keyed twice, then the key never changes.
def test_record_key_is_stable_across_calls() -> None:
    first = loader.record_key("b" * 64, "life-individual-term-007")
    second = loader.record_key("b" * 64, "life-individual-term-007")

    assert first == second


# Given a different dataset, when keyed, then the reserved key differs.
def test_record_key_changes_with_the_dataset() -> None:
    assert loader.record_key("a" * 64, "case-1") != loader.record_key(
        "c" * 64, "case-1"
    )


# Given unordered records, when ordered, then the sequence is deterministic.
def test_records_load_in_a_deterministic_order() -> None:
    records = [
        {"case_id": "motor-002"},
        {"case_id": "life-001"},
        {"case_id": "motor-001"},
    ]

    ordered = loader.ordered_records(records)

    assert [record["case_id"] for record in ordered] == [
        "life-001",
        "motor-001",
        "motor-002",
    ]
    assert loader.ordered_records(records) == ordered


# Given a completed load, when reported, then only safe fields are emitted.
def test_success_output_reports_only_safe_fields() -> None:
    result = loader.success_result(
        environment="development",
        dataset_sha256="d" * 64,
        expected_count=90,
        created_count=90,
        resumed_count=0,
        verified_count=90,
    )

    assert set(result) == SAFE_SUCCESS_KEYS
    assert result["complete"] is True


# Given a refused or failed load, when reported, then it stays sanitized.
def test_failure_output_reports_only_safe_fields() -> None:
    result = loader.failure_result(
        environment="production",
        error_code=loader.ERROR_FORBIDDEN,
    )

    assert set(result) <= SAFE_FAILURE_KEYS
    assert result["complete"] is False
    assert result["error_code"] == "evaluation_load_forbidden"


# Given any failure detail, when reported, then no payload or path leaks.
def test_failure_output_rejects_unsafe_detail() -> None:
    result = loader.failure_result(
        environment="development",
        error_code=loader.ERROR_COLLISION,
        source_case_id="motor-private-car-001",
        stage="documents",
    )

    text = str(result)
    for unsafe in ("password", "/data/uploads", "postgresql", "Bearer"):
        assert unsafe not in text


# Given a record collision whose case ID came from a malformed corpus
# record, when it is reported, then the unsafe field is dropped: every
# failure path shares the same sanitization, not only the CLI's own catch.
def test_collision_output_omits_a_malformed_source_case_id() -> None:
    result = loader.failure_result(
        environment="development",
        error_code=loader.ERROR_COLLISION,
        dataset_sha256="e" * 64,
        source_case_id=12345,
        stage="workflow",
    )

    assert "source_case_id" not in result
    assert result["stage"] == "workflow"


# Given a record collision whose case ID is an implausibly long, secret-
# shaped string, when it is reported, then it never reaches standard output.
def test_collision_output_omits_an_oversized_source_case_id() -> None:
    result = loader.failure_result(
        environment="development",
        error_code=loader.ERROR_COLLISION,
        dataset_sha256="e" * 64,
        source_case_id="Bearer synthetic-secret-token-" + "x" * 500,
        stage="workflow",
    )

    assert "source_case_id" not in result


# Given a short secret-shaped string standing in for a source case ID, when
# it is reported, then it never reaches standard output: a length check
# alone is not enough, the value must also be a safe identifier.
@pytest.mark.parametrize(
    "source_case_id",
    [
        "Bearer synthetic-secret-token",
        "eyJhbGciOiJIUzI1NiJ9.synthetic",
        "case id with spaces",
        "../traversal",
    ],
)
def test_collision_output_omits_a_secret_shaped_source_case_id(
    source_case_id,
) -> None:
    result = loader.failure_result(
        environment="development",
        error_code=loader.ERROR_COLLISION,
        dataset_sha256="e" * 64,
        source_case_id=source_case_id,
        stage="workflow",
    )

    assert "source_case_id" not in result


# Given a valid corpus-shaped source case ID, when it is reported, then it
# is kept, so genuine collision detail is not also thrown away.
def test_collision_output_keeps_a_safe_source_case_id() -> None:
    result = loader.failure_result(
        environment="development",
        error_code=loader.ERROR_COLLISION,
        dataset_sha256="e" * 64,
        source_case_id="motor-private-car-001",
        stage="workflow",
    )

    assert result["source_case_id"] == "motor-private-car-001"


# Given the loader, when it selects a provider, then only the deterministic
# fake provider can run, never a network-backed one.
def test_loader_runs_only_the_deterministic_fake_provider() -> None:
    assert loader.PROVIDER_FACTORY is FakeProvider

    source = Path(loader.__file__).read_text()

    for forbidden in ("build_provider", "GeminiProvider", "OllamaProvider"):
        assert forbidden not in source


# Given production, when the loader runs, then it refuses before opening any
# database or upload storage.
@pytest.mark.asyncio
async def test_production_is_refused_before_persistence_opens(
    monkeypatch,
) -> None:
    opened: list[str] = []

    # Record any attempt to construct persistence during a refused load.
    def _record(name: str):
        def _factory(*args, **kwargs):
            opened.append(name)
            raise AssertionError(f"{name} must not be constructed")

        return _factory

    monkeypatch.setattr(loader, "Database", _record("Database"))
    monkeypatch.setattr(loader, "UploadStorage", _record("UploadStorage"))

    result = await loader.load_evaluation_data(
        settings=Settings(_env_file=None, environment_mode="production")
    )

    assert opened == []
    assert result == {
        "environment": "production",
        "complete": False,
        "error_code": "evaluation_load_forbidden",
    }


# Given a rejected corpus preflight, when the CLI runs, then it prints one
# sanitized JSON object and never a raw traceback.
def test_preflight_failure_is_reported_without_a_traceback(
    monkeypatch, capsys
) -> None:
    async def _raise(*args, **kwargs):
        raise loader.DatasetPreflightError("case-1", "case_count")

    monkeypatch.setattr(loader, "load_evaluation_data", _raise)

    exit_code = loader.main()

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "environment": "development",
        "complete": False,
        "error_code": "evaluation_load_preflight_failed",
        "source_case_id": "case-1",
        "stage": "preflight",
    }


# Given an unexpected internal failure, when the CLI runs, then it still
# prints one sanitized JSON object and never a raw traceback or exception
# message.
def test_unexpected_failure_is_reported_without_a_traceback(
    monkeypatch, capsys
) -> None:
    async def _raise(*args, **kwargs):
        raise RuntimeError("synthetic-internal-detail")

    monkeypatch.setattr(loader, "load_evaluation_data", _raise)

    exit_code = loader.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    assert "synthetic-internal-detail" not in captured.out
    output = json.loads(captured.out)
    assert output == {
        "environment": "development",
        "complete": False,
        "error_code": "evaluation_load_failed",
    }


# Given settings that fail to validate, when the CLI runs, then it still
# prints one sanitized JSON object and never a raw traceback, even though
# the failure handler cannot read the environment mode either.
def test_settings_validation_failure_is_reported_without_a_traceback(
    monkeypatch, capsys
) -> None:
    def _raise():
        raise ValueError("synthetic-invalid-environment-mode")

    monkeypatch.setattr(loader, "get_settings", _raise)

    exit_code = loader.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    assert "synthetic-invalid-environment-mode" not in captured.out
    output = json.loads(captured.out)
    assert output == {
        "environment": "unknown",
        "complete": False,
        "error_code": "evaluation_load_failed",
    }


# Given a preflight rejection whose case ID came from a malformed corpus
# record, when the CLI runs, then an unsafe field is dropped instead of
# reaching standard output verbatim.
def test_preflight_failure_omits_a_malformed_source_case_id(
    monkeypatch, capsys
) -> None:
    async def _raise(*args, **kwargs):
        raise loader.DatasetPreflightError(12345, "case_count")

    monkeypatch.setattr(loader, "load_evaluation_data", _raise)

    exit_code = loader.main()

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "environment": "development",
        "complete": False,
        "error_code": "evaluation_load_preflight_failed",
        "stage": "preflight",
    }


# Given a preflight rejection whose case ID is an implausibly long string,
# when the CLI runs, then it is dropped instead of flooding standard output.
def test_preflight_failure_omits_an_oversized_source_case_id(
    monkeypatch, capsys
) -> None:
    async def _raise(*args, **kwargs):
        raise loader.DatasetPreflightError("x" * 500, "case_count")

    monkeypatch.setattr(loader, "load_evaluation_data", _raise)

    exit_code = loader.main()

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert "source_case_id" not in output
