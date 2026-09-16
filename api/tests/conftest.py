"""Make the shared `fixtures` package importable from every suite.

Pytest adds a collected module's own directory to the import path, so a test
in `tests/integration` cannot reach `tests/fixtures` on its own. Loading this
conftest at the tests root puts that root on the path once, for every suite,
instead of each suite inserting paths for itself.
"""
