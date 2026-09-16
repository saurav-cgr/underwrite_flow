"""Make the canonical synthetic fixtures importable by this suite.

The deterministic PDF builders live beside the integration suite. Pytest adds
only a test module's own directory to the import path, so the path is added
here rather than relying on which modules a given run happens to collect.
"""

import sys
from pathlib import Path

INTEGRATION_DIR = Path(__file__).resolve().parent.parent / "integration"

if str(INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_DIR))
