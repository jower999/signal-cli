# signal-cli

A reusable Python library and CLI for sending text messages and images via [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api).

It supports sending to both **Signal groups** and **individual phone numbers**, and can discover groups your linked account is a member of.

## Installation

```bash
pip install signal-cli
```

For CLI usage via isolated environment:

```bash
pipx install signal-cli
```

## Quick Start

### As a Library

```python
from signal_cli import SignalClient, SignalConfig

# Load from default config (~/.golfmanager/signal.json)
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

By default, configuration is stored at `~/.golfmanager/signal.json`.

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

The recommended compose file is installed to `~/.golfmanager/docker-compose.signal.yml`.

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