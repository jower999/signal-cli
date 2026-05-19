import tempfile
from pathlib import Path
import pytest

from signal_cli.config import SignalConfig


@pytest.fixture
def temp_config_path():
    """Provide a temporary config file path for isolated tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test-signal.json"
        yield path


@pytest.fixture
def config_with_legacy_groups(temp_config_path):
    """Create a SignalConfig file that still uses the old 'groups' key (for migration testing)."""
    data = {
        "number": "+46700000001",
        "api_url": "http://localhost:8080",
        "groups": {
            "team": "group.ABC123",
            "boss": "+46700000002",
        },
    }
    temp_config_path.write_text(str(data).replace("'", '"'))  # simple json-like
    # Better to write proper JSON
    import json
    temp_config_path.write_text(json.dumps(data, indent=2))
    return temp_config_path