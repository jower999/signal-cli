# Changelog

All notable changes to the `signal-cli` Python package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05

### Added
- First public release as standalone `signal-cli` package.
- Support for sending to both Signal groups **and individuals** (phone numbers) via `--recipient` / `-r`.
- `SignalClient.list_remote_groups()` — fetch live groups from the linked account.
- Interactive `group list --available` command that can save discovered groups with friendly names.
- `SignalConfig` now supports custom config paths and environment variable `SIGNAL_CLI_CONFIG`.
- One-time automatic migration from legacy `"groups"` key to `"recipients"`.
- Clean public API: `from signal_cli import SignalClient, SignalConfig`.

### Changed
- Package renamed from `golfmanager-signal` to `signal-cli`.
- Console script renamed from `golfmanager-signal` to `signal-cli`.
- Default Docker container name changed to `signal-cli`.
- Removed `register` and `verify` commands (the tool is now intended for linked-device use only).
- `send` command now uses `--recipient` / `-r` as the primary flag (`--group` / `-g` remains as a backward-compatible alias).

### Removed
- `register` and `verify` commands and all associated captcha/SMS registration flow code.

### Fixed
- Various improvements to recipient resolution and error messaging.

## [0.1.0] - Previous internal releases

Initial versions were distributed internally as part of the Golfmanager monorepo under the name `golfmanager-signal`.