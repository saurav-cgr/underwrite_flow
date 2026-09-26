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
MAKEFILE_PATH = Path("/Makefile")

LOADER_SCRIPT = "load_evaluation_data"


# Return the lines of one Makefile target, up to the next unindented line.
def _target_body(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line == f"{name}:")
    body = []
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        body.append(line)
    return "\n".join(body)


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


# Verify one explicit command loads the corpus into the isolated evaluation
# stack, distinct from the command that targets development.
def test_evaluation_load_command_targets_the_evaluation_stack() -> None:
    if not MAKEFILE_PATH.exists():
        pytest.skip("Makefile is not mounted into the api service")
    text = MAKEFILE_PATH.read_text()

    body = _target_body(text, "load-evaluation-data-eval")

    assert "compose.evaluation.yaml" in body
    assert "evaluation-api" in body
    assert LOADER_SCRIPT in body
    assert "EVALUATION_LOADER_ACTOR_TOKEN" in body


# Verify the loader runs inside the already-running evaluation API container,
# never a fresh one-off container: its tmpfs upload volume exists only for
# one container's lifetime, so a separate `run` container's uploads would be
# invisible to the API the operator actually queries afterward.
def test_evaluation_load_command_targets_the_running_api_container() -> None:
    if not MAKEFILE_PATH.exists():
        pytest.skip("Makefile is not mounted into the api service")
    text = MAKEFILE_PATH.read_text()

    body = _target_body(text, "load-evaluation-data-eval")

    assert "up -d" in body
    assert "exec" in body
    assert "run --rm" not in body


# Merge one override onto the base stack the way Compose renders it, so the
# test reads the same effective service definitions the operator runs.
def _rendered_production() -> dict[str, Any]:
    base = _load_compose(BASE_PATH)
    override = _load_compose(PRODUCTION_PATH)
    services = {name: dict(service) for name, service in
                base["services"].items()}
    for name, patch in (override.get("services") or {}).items():
        merged = dict(services.get(name, {}))
        for key, value in patch.items():
            if key == "environment":
                merged["environment"] = {
                    **_environment(services.get(name, {})),
                    **_environment({"environment": value}),
                }
            else:
                merged[key] = value
        services[name] = merged
    return {**base, "services": services}


# Verify the rendered production stack gives the API production mode.
def test_rendered_production_stack_sets_production_mode() -> None:
    rendered = _rendered_production()

    assert (
        _environment(rendered["services"]["api"])["ENVIRONMENT_MODE"]
        == "production"
    )
    assert (
        _environment(rendered["services"]["bootstrap"])["ENVIRONMENT_MODE"]
        == "production"
    )


# Verify the rendered production stack keeps the common baseline bootstrap.
def test_rendered_production_stack_keeps_the_baseline_bootstrap() -> None:
    rendered = _rendered_production()

    command = _command_text(rendered["services"]["bootstrap"])
    assert "alembic upgrade head" in command
    assert "import_configs" in command


# Verify no rendered production service loads evaluation data on startup.
def test_rendered_production_stack_never_loads_data() -> None:
    rendered = _rendered_production()

    for name, service in rendered["services"].items():
        assert LOADER_SCRIPT not in _command_text(service), name
        assert LOADER_SCRIPT not in str(service.get("entrypoint") or ""), name
