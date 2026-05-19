import json

from signal_cli.config import SignalConfig


def test_load_with_legacy_groups_migrates_to_recipients(config_with_legacy_groups):
    """Loading a config that still has the old 'groups' key should migrate to 'recipients'."""
    cfg = SignalConfig.load(config_with_legacy_groups)

    assert "team" in cfg.recipients
    assert cfg.recipients["team"] == "group.ABC123"
    assert "boss" in cfg.recipients

    # After load + save, the file should no longer contain the old key
    data = json.loads(config_with_legacy_groups.read_text())
    assert "recipients" in data
    assert "groups" not in data


def test_custom_config_path(temp_config_path):
    """SignalConfig should respect an explicit config_path."""
    cfg = SignalConfig(config_path=temp_config_path)
    cfg.number = "+123456"
    cfg.recipients["test"] = "group.TEST"
    cfg.save()

    assert temp_config_path.exists()

    # Load it back
    cfg2 = SignalConfig.load(temp_config_path)
    assert cfg2.number == "+123456"
    assert cfg2.recipients["test"] == "group.TEST"


def test_load_nonexistent_path_returns_empty_config(temp_config_path):
    """Loading a path that does not exist should return a default config."""
    cfg = SignalConfig.load(temp_config_path)
    assert cfg.number is None
    assert cfg.recipients == {}
