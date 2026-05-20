# Changelog

All notable changes to the `signal-cli` Python package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-05-20

### Added
- `signal-cli link` (and `golfmanager signal link`) now automatically manages a short-lived
  ephemeral container (`signal-cli-link`) running with `MODE=native` for reliable device
  linking. The user's normal service (whatever MODE they have chosen in their compose file)
  is stopped only for the duration of linking and restarted afterwards. The container is
  guaranteed to be cleaned up even on Ctrl-C, unhandled exceptions, or process termination
  (bulletproof atexit + signal handling). This works for both the standalone Python CLI and
  the Golfmanager C# wrapper.

### Changed
- Reverted the packaged `docker-compose.yml` default from `MODE=native` back to `MODE=json-rpc`.
  `json-rpc` (long-lived JVM daemon) is now the default again for best steady-state
  performance and lower resource usage. Linking compatibility notes and instructions
  have been updated in the template, CLI, README, and sibling golfmanager.aspire docs.
  Use `MODE=native` (or `normal`) only as a temporary workaround if you hit
  `UnsupportedOperationException` during initial device linking.

## [0.4.0] - 2026-05

### Added
- Automatic provisioning of a recommended `docker-compose.yml` when running `signal-cli setup`.
- New public helpers: `install_docker_compose()`, `get_docker_compose_path()`, `get_docker_compose_template()`.
- The packaged `docker-compose.yml` now defaults to `MODE=native` (instead of `json-rpc`) for better device linking compatibility and fewer `UnsupportedOperationException` issues during QR code linking.

### Changed
- `signal-cli setup` now writes (or detects) the docker compose file under `~/.signal-cli/docker-compose.yml`.
- Improved error messaging when linking fails due to mode incompatibility (now points to the actual compose file location).
- Bumped package version to 0.4.0.

### Fixed
- Error message incorrectly referenced a non-existent `docker-compose.signal.yml` file.

## [0.3.0] - Unreleased

### Changed
- Internal preparation for docker compose management (shipped in 0.4.0).

## [0.2.0] - 2026-05

### Added
- First public release as standalone `signal-cli` package (published to PyPI as `signal-cli-py` due to an existing older package with the same name).
- Support for sending to both Signal groups **and individuals** (phone numbers) via `--recipient` / `-r`.
- `SignalClient.list_remote_groups()` — fetch live groups from the linked account.
- Interactive `group list --available` command that can save discovered groups with friendly names.
- `SignalConfig` now supports custom config paths and environment variable `SIGNAL_CLI_CONFIG`.
- One-time automatic migration from legacy `"groups"` key to `"recipients"`.
- Clean public API: `from signal_cli import SignalClient, SignalConfig`.

### Changed
- Package extracted as a standalone library/CLI (previously internal).
- Default Docker container name changed to `signal-cli`.
- Removed `register` and `verify` commands (the tool is now intended for linked-device use only).
- `send` command now uses `--recipient` / `-r` as the primary flag (`--group` / `-g` remains as a backward-compatible alias).

### Removed
- `register` and `verify` commands and all associated captcha/SMS registration flow code.

### Fixed
- Various improvements to recipient resolution and error messaging.

## [0.1.0] - Previous internal releases

Early development happened inside a larger project before being extracted as a standalone package.