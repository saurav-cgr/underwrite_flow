"""Unit coverage for the validated environment mode boundary.

The loader needs one process-owned answer before it opens persistence, so
these tests pin the exact enum, the local default, and the derived rule that
evaluation loading is allowed everywhere except production.
"""

import pytest
from pydantic import ValidationError

from underwriteflow.config import Settings


# Given no configured mode, when settings load, then development is used.
def test_environment_mode_defaults_to_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment_mode == "development"


# Given each supported mode, when settings load, then the value is kept.
@pytest.mark.parametrize(
    "mode", ["development", "evaluation", "production"]
)
def test_supported_environment_modes_are_accepted(mode: str) -> None:
    settings = Settings(_env_file=None, environment_mode=mode)

    assert settings.environment_mode == mode


# Given an unsupported mode, when settings load, then startup is prevented.
@pytest.mark.parametrize(
    "mode", ["staging", "PRODUCTION", "", "dev", "production ", "test"]
)
def test_unsupported_environment_mode_prevents_startup(mode: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment_mode=mode)


# Given a non-production mode, when derived, then loading is allowed.
@pytest.mark.parametrize("mode", ["development", "evaluation"])
def test_evaluation_loading_is_allowed_outside_production(mode: str) -> None:
    settings = Settings(_env_file=None, environment_mode=mode)

    assert settings.evaluation_loading_allowed is True


# Given production, when derived, then evaluation loading is refused.
def test_evaluation_loading_is_refused_in_production() -> None:
    settings = Settings(_env_file=None, environment_mode="production")

    assert settings.evaluation_loading_allowed is False


# Given a loaded settings object, when mutated, then the mode stays fixed.
def test_environment_mode_is_fixed_for_the_process() -> None:
    settings = Settings(_env_file=None, environment_mode="production")

    with pytest.raises(ValidationError):
        settings.environment_mode = "development"

    assert settings.environment_mode == "production"
    assert settings.evaluation_loading_allowed is False
