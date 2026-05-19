# Contributing to signal-cli

Thank you for your interest in contributing to `signal-cli`!

## Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   # .venv\Scripts\activate       # Windows
   ```
3. Install the package in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Run the tests:
   ```bash
   pytest
   ```

## Code Style

- We use `black` and `ruff` for formatting and linting (to be added to the dev dependencies).
- Keep the public API in `signal_cli/__init__.py` minimal and well-documented.
- New features should include tests in the `tests/` directory.

## Making Changes

1. Create a feature branch from `main`.
2. Make your changes.
3. Add or update tests as needed.
4. Run `pytest` to ensure everything still works.
5. Open a Pull Request with a clear description of the change.

## Releasing

Releases are handled via GitHub Releases. When a new release is published, the GitHub Actions workflow will automatically build the package and publish it to PyPI using Trusted Publishing.

## Questions?

Feel free to open an issue for bugs, feature requests, or questions.