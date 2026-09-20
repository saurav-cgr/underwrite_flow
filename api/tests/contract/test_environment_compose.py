"""Contract coverage for explicit Compose environment modes.

Each Compose file is read and parsed directly, the same way a rendered
`docker compose config` would be read, so these tests need no running stack.
The development stack mounts them read-only beside the evaluation stack.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

BASE_PATH = Path("/compose.yaml")
EVALUATION_PATH = Path("/compose.evaluation.yaml")
PRODUCTION_PATH = Path("/compose.production.yaml")

LOADER_SCRIPT = "load_evaluation_data"


# Parse one mounted Compose file, skipping until it is mounted read-only.
def _load_compose(path: Path) -> dict[str, Any]:
    if not path.exists():
        pytest.skip(f"{path.name} is not mounted into the api service")
    return yaml.safe_load(path.read_text())


# Read one service's environment mapping as plain strings.
def _environment(service: dict[str, Any]) -> dict[str, str]:
    environment = service.get("environment") or {}
    if isinstance(environment, list):
        pairs = [str(item).split("=", 1) for item in environment]
        return {pair[0]: (pair[1] if len(pair) > 1 else "") for pair in pairs}
    return {str(key): str(value) for key, value in environment.items()}


# Flatten one service's command into a single searchable string.
def _command_text(service: dict[str, Any]) -> str:
    command = service.get("command") or []
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


# Verify the development stack declares its mode explicitly.
def test_base_compose_declares_development_mode() -> None:
    compose = _load_compose(BASE_PATH)

    for name in ("api", "bootstrap"):
        environment = _environment(compose["services"][name])
        assert "ENVIRONMENT_MODE" in environment, name
        assert "development" in environment["ENVIRONMENT_MODE"], name


# Verify the isolated evaluation stack declares evaluation mode.
def test_evaluation_compose_declares_evaluation_mode() -> None:
    compose = _load_compose(EVALUATION_PATH)

    environment = _environment(compose["services"]["evaluation-api"])
    assert environment.get("ENVIRONMENT_MODE") == "evaluation"


# Verify the production override selects production mode for the API.
def test_production_override_declares_production_mode() -> None:
    compose = _load_compose(PRODUCTION_PATH)

    environment = _environment(compose["services"]["api"])
    assert environment.get("ENVIRONMENT_MODE") == "production"


# Verify the production override changes mode only, adding no new service.
def test_production_override_adds_no_service() -> None:
    base = _load_compose(BASE_PATH)
    override = _load_compose(PRODUCTION_PATH)

    assert set(override["services"]) <= set(base["services"])


# Verify no startup command in any stack runs the evaluation loader.
@pytest.mark.parametrize(
    "path", [BASE_PATH, EVALUATION_PATH, PRODUCTION_PATH]
)
def test_no_service_command_runs_the_loader(path: Path) -> None:
    compose = _load_compose(path)

    for name, service in (compose.get("services") or {}).items():
        assert LOADER_SCRIPT not in _command_text(service), name
        assert LOADER_SCRIPT not in str(service.get("entrypoint") or ""), name
