"""Focused recovery tests for the deterministic Compose smoke flow."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from smoke import SYNTHETIC_DOCUMENT, recover_case


class Response:
    """Provide the small HTTP response surface used by the smoke helper."""

    # Store a successful JSON response.
    def __init__(self, payload: dict) -> None:
        self.status_code = 200
        self._payload = payload
        self.text = ""

    # Return the configured JSON response.
    def json(self) -> dict:
        return self._payload


class Client:
    """Record recovery calls while returning deterministic API responses."""

    # Configure the case status and already-uploaded filenames.
    def __init__(self, status: str, filenames: list[str] | None = None) -> None:
        self.status = status
        self.filenames = filenames or []
        self.calls: list[tuple[str, str, dict]] = []

    # Return documents currently attached to the synthetic case.
    def get(self, path: str, **kwargs: dict) -> Response:
        self.calls.append(("get", path, kwargs))
        return Response([{"filename": filename} for filename in self.filenames])

    # Return the status-specific response for every recovery request.
    def post(self, path: str, **kwargs: dict) -> Response:
        self.calls.append(("post", path, kwargs))
        if path.endswith("/start"):
            return Response({"recommendation": {"route": "expedited"}})
        if path.startswith("/api/v1/reviews/"):
            return Response({"status": "confirmed"})
        return Response({"status": "completed", "handoff_id": "synthetic"})


# Verify every valid persisted smoke status completes or resumes safely.
@pytest.mark.parametrize(
    ("status", "expected_posts"),
    [
        ("new", 5),
        ("underwriter_review", 2),
        ("confirmed", 1),
        ("overridden", 1),
        ("completed", 1),
    ],
)
def test_recover_case_handles_each_recoverable_status(
    status: str, expected_posts: int
) -> None:
    client = Client(status)

    completion = recover_case(
        client,
        {"id": "case-id", "status": status},
        {"Authorization": "Bearer applicant"},
        {"Authorization": "Bearer underwriter"},
    )

    assert completion == {"status": "completed", "handoff_id": "synthetic"}
    posts = [call for call in client.calls if call[0] == "post"]
    assert len(posts) == expected_posts


# Verify a resumed new case uploads only the missing synthetic document.
def test_recover_case_skips_existing_documents() -> None:
    client = Client("new", ["identity.pdf"])

    recover_case(
        client,
        {"id": "case-id", "status": "new"},
        {"Authorization": "Bearer applicant"},
        {"Authorization": "Bearer underwriter"},
    )

    uploads = [call for call in client.calls if "/documents" in call[1]]
    assert len(uploads) == 2
    assert uploads[0][0] == "get"
    assert uploads[1][2]["files"]["document"] == (
        "vehicle.pdf",
        SYNTHETIC_DOCUMENT,
        "application/pdf",
    )
