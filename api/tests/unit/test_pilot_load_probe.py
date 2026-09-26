"""Focused checks for the synthetic pilot probe helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from pilot_load_probe import fresh_case_key, percentile


# Verify every cohort and invocation receives a distinct intake key.
def test_fresh_case_keys_do_not_reuse_cases() -> None:
    first = fresh_case_key("run-a", 10, 0)

    assert first != fresh_case_key("run-b", 10, 0)
    assert first != fresh_case_key("run-a", 100, 0)
    assert first != fresh_case_key("run-a", 10, 1)


# Verify p95 uses the nearest-rank value for small bounded samples.
def test_percentile_uses_nearest_rank() -> None:
    assert percentile([4.0, 1.0, 3.0, 2.0], 95) == 4.0
    assert percentile([7.0], 95) == 7.0
