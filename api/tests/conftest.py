"""Make the shared `fixtures` package importable from every suite.

Pytest adds a collected module's own directory to the import path, so a test
in `tests/integration` cannot reach `tests/fixtures` on its own. Loading this
conftest at the tests root puts that root on the path once, for every suite,
instead of each suite inserting paths for itself.
"""

import pytest

from fixtures.records import motor_status, set_motor_status


# Put product activation back the way the run found it, so a test that
# activates a product cannot leave the developer's demo stack with an empty
# applicant catalogue.
@pytest.fixture(scope="session", autouse=True)
def restore_product_status():
    try:
        found = motor_status()
    except Exception:
        # A suite that never reaches the database must not require it here.
        yield
        return
    yield
    set_motor_status(found)
