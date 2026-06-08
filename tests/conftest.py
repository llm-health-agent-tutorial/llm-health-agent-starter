import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # so `import ha_workshop` (top-level) resolves under pytest

import pytest  # noqa: E402

from healthagent.llm.client import get_client  # noqa: E402


@pytest.fixture
def scripted():
    return get_client("scripted", quiet=True)
