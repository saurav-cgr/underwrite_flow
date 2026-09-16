"""Shared synthetic fixtures for every test suite.

Modules here build deterministic documents, drive the public API, and seed or
inspect rows directly. Both `tests/integration` and `tests/contract` import
them, which is why they live in one package instead of beside one suite.
"""
