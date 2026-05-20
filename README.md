# signal-cli

A reusable Python library and CLI for sending text messages and images via [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api).

It supports sending to both **Signal groups** and **individual phone numbers**, and can discover groups your linked account is a member of.

## Installation

```bash
pip install signal-cli-py
```

For CLI usage via isolated environment (recommended):

```bash
pipx install signal-cli-py
```

> **Note**: After installing, the command is still `signal-cli` (not `signal-cli-py`).  
> Example: `signal-cli send --recipient team "Hello"`
> 
> This is intentional — the PyPI package name is `signal-cli-py` to avoid a naming conflict with an older package.

## Quick Start

### As a Library

```python
from signal_cli import SignalClient, SignalConfig

# Load from default config (~/.signal-cli/config.json)
client = SignalClient()

# Send to a saved recipient (group or phone number)
client.send("Hello from Python", recipient="team-updates")

# Send with an image
client.send(
    "Weekly report",
    recipient="+46700000001",
    attachments=[{"filename": "report.png", "data": base64_data}]
)

# Discover live groups from your linked account
groups = client.list_remote_groups()
for g in groups:
    print(g["name"], g["id"])
```

### As a CLI

```bash
# Basic setup (stores number + API URL)
signal-cli setup

# List groups your linked account can see
signal-cli group-list --available

# Send a message
signal-cli send --recipient team-updates "Hello team"

# Send with image
signal-cli send --recipient team-updates --image ./chart.png "Weekly update"
```

## Configuration

By default, configuration is stored at `~/.signal-cli/config.json`.

You can override the config location in two ways:

```python
# Explicit path
cfg = SignalConfig(config_path="/path/to/my-signal.json")
client = SignalClient(config=cfg)

# Via environment variable
export SIGNAL_CLI_CONFIG=/path/to/my-signal.json
```

## Important: Linked Device Behavior

This tool is designed to be used as a **linked device** (not a primary registration).

- New groups created on your phone may not immediately appear when calling `list_remote_groups()` or `group-list --available`.
- Common triggers that make new groups visible:
  - Send/receive a message inside the group from your phone
  - Restart the `signal-cli-rest-api` container
  - Re-link the device (most reliable)

If a group is missing, the recommended first step is to send a message in it from your phone and then re-check.

## Docker Requirement

Sending requires a running `signal-cli-rest-api` container (usually managed via Docker Compose).

The recommended compose file is automatically installed to `~/.signal-cli/docker-compose.yml`
when you run `signal-cli setup` (or you can manage it yourself).

This package defaults to `MODE=json-rpc` in the generated compose file (long-lived
JVM daemon) for the best performance and resource characteristics in normal use.

The `link` command automatically starts a short-lived container using `MODE=native`
(the most reliable configuration for device linking) when it detects the standard
local compose file. Your normal service is left exactly as you configured it and is
restarted after linking. You should not need to edit the compose file for linking.

## Development

```bash
cd signal-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT