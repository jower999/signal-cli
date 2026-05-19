from pathlib import Path
import json
import os
import warnings
from typing import Dict, Optional, Union

# Default configuration directory for standalone use.
DEFAULT_CONFIG_DIR = Path.home() / ".signal-cli"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


class SignalConfig:
    """
    Configuration for the Signal delivery client.

    Supports:
    - Custom config file location (constructor or SIGNAL_CLI_CONFIG env var)
    - Backward compatibility with very old config files that used "groups" instead of "recipients"
    - Named shortcuts that can point to either Signal groups or individual phone numbers
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self._config_path = self._resolve_config_path(config_path)

        self.number: Optional[str] = None
        self.api_url: str = "http://localhost:8080"

        # Canonical storage (new name)
        self.recipients: Dict[str, str] = {}

        # Legacy compatibility shim (see @property below)
        self._migrated_from_groups = False

    # --------------------------------------------------------------------- #
    # Path resolution
    # --------------------------------------------------------------------- #
    def _resolve_config_path(self, explicit: Optional[Union[str, Path]]) -> Path:
        if explicit:
            return Path(explicit).expanduser()
        env = os.environ.get("SIGNAL_CLI_CONFIG")
        if env:
            return Path(env).expanduser()
        return DEFAULT_CONFIG_FILE

    @property
    def config_path(self) -> Path:
        """The actual path this config instance will read from / write to."""
        return self._config_path

    # --------------------------------------------------------------------- #
    # Legacy "groups" compatibility shim
    # --------------------------------------------------------------------- #
    @property
    def groups(self) -> Dict[str, str]:
        """Backward-compat alias. Prefer .recipients in new code."""
        warnings.warn(
            "SignalConfig.groups is deprecated and will be removed in 0.3.0. "
            "Use .recipients instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipients

    @groups.setter
    def groups(self, value: Dict[str, str]):
        warnings.warn(
            "SignalConfig.groups is deprecated and will be removed in 0.3.0. "
            "Use .recipients instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.recipients = value

    # --------------------------------------------------------------------- #
    # Persistence
    # --------------------------------------------------------------------- #
    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "SignalConfig":
        config = cls(config_path=config_path)
        path = config._config_path

        if not path.exists():
            return config

        try:
            data = json.loads(path.read_text())
        except Exception:
            # Corrupt file — start fresh but keep the path
            return config

        config.number = data.get("number")
        config.api_url = data.get("api_url", config.api_url)

        # New key takes precedence
        if "recipients" in data:
            config.recipients = data.get("recipients", {}) or {}
        elif "groups" in data:
            # One-time migration from legacy "groups" key (very old config files)
            config.recipients = data.get("groups", {}) or {}
            config._migrated_from_groups = True

        # Auto-clean the file on first migration so users don't keep the old key forever
        if config._migrated_from_groups:
            try:
                config.save()
            except Exception:
                pass  # non-fatal

        return config

    def save(self) -> None:
        """Persist configuration. Always writes under the modern 'recipients' key."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        data: Dict[str, object] = {
            "number": self.number,
            "api_url": self.api_url,
            "recipients": self.recipients,
        }

        # If we migrated on this run, we already dropped the old key by not writing it.
        self._config_path.write_text(json.dumps(data, indent=2))

    # --------------------------------------------------------------------- #
    # Resolution helpers
    # --------------------------------------------------------------------- #
    def resolve_recipient(self, name_or_id: str) -> str:
        """
        Resolve a friendly name (or raw ID/phone) to the actual Signal recipient.

        Works for both saved group IDs and saved individual phone numbers.
        If the value is not a known name, it is returned as-is (assumed to be
        a raw group ID or phone number).
        """
        return self.recipients.get(name_or_id, name_or_id)

    # Keep old name working during the transition period (used by SignalClient today)
    def get_group_id(self, name_or_id: str) -> str:
        """Deprecated alias for resolve_recipient. Will be removed in 0.3.0."""
        warnings.warn(
            "get_group_id() is deprecated, use resolve_recipient() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.resolve_recipient(name_or_id)
