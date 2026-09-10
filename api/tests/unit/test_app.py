from fastapi.testclient import TestClient

from underwriteflow.app import create_app


class ReadyDatabase:
    """Deterministic ready-check double."""

    # Simulate a successful database health check.
    async def ping(self) -> None:
        return None


# Verify health succeeds without a live provider.
def test_health_is_provider_independent() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Verify unknown routes use the stable error contract.
def test_unknown_route_returns_sanitized_error() -> None:
    client = TestClient(create_app())

    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Resource not found",
        "request_id": response.headers["X-Request-ID"],
        "retryable": False,
    }


# Verify API namespace has a stable composition root.
def test_api_v1_root_is_available() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"status": "available"}


# Verify readiness depends on the database boundary only.
def test_ready_checks_database() -> None:
    app = create_app()
    app.state.database = ReadyDatabase()
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


# Verify local browser origin receives CORS headers.
def test_health_allows_local_web_origin() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
