"""Contract coverage for the standalone isolated evaluation Compose stack.

`compose.evaluation.yaml` (T048) is read and parsed directly, the same way a
rendered `docker compose config` would be read, so these tests need no
running stack. They fail with a clear skip until that file exists.
"""

from pathlib import Path

import pytest
import yaml

COMPOSE_PATH = (
    Path(__file__).resolve().parents[3] / "compose.evaluation.yaml"
)


# Parse the standalone evaluation stack, skipping until T048 adds it.
def _load_compose() -> dict:
    if not COMPOSE_PATH.exists():
        pytest.skip("compose.evaluation.yaml not yet added (T048)")
    return yaml.safe_load(COMPOSE_PATH.read_text())


# Verify the stack is named apart from the development Compose project.
def test_stack_has_its_own_project_name() -> None:
    compose = _load_compose()

    assert compose.get("name") == "underwriteflow-evaluation"


# Verify no service exposes a host port, so it cannot collide with dev.
def test_no_service_publishes_a_host_port() -> None:
    compose = _load_compose()

    for name, service in compose["services"].items():
        assert "ports" not in service, name


# Verify no named, durable volume is declared for this disposable stack.
def test_no_named_volume_is_declared() -> None:
    compose = _load_compose()

    assert not compose.get("volumes")


# Verify no service references an external, shared development network.
def test_no_service_joins_an_external_network() -> None:
    compose = _load_compose()

    for network in (compose.get("networks") or {}).values():
        assert not (network or {}).get("external")
    for name, service in compose["services"].items():
        assert "network_mode" not in service, name


# Verify the runner has no database URL, Docker socket, or dev credential.
def test_runner_has_no_database_url_or_docker_socket() -> None:
    compose = _load_compose()
    runner = compose["services"]["evaluation-runner"]

    environment = runner.get("environment") or {}
    assert not any("DATABASE_URL" in str(key) for key in environment)
    for volume in runner.get("volumes") or []:
        assert "docker.sock" not in str(volume)


# Verify the API only ever runs the fake provider with tracing disabled.
def test_api_uses_fake_provider_with_tracing_and_keys_disabled() -> None:
    compose = _load_compose()
    api_environment = compose["services"]["evaluation-api"]["environment"]

    assert str(api_environment["GENERATION_PROVIDER"]) == "fake"
    assert str(api_environment["PROVIDER_RETRY_COUNT"]) == "0"
    assert str(api_environment["LANGSMITH_TRACING"]).lower() == "false"
    assert not api_environment.get("GEMINI_API_KEY")
    assert not api_environment.get("LANGSMITH_API_KEY")
