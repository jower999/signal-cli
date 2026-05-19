.PHONY: install dev test lint format clean build publish-check

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

lint:
	ruff check .
	black --check .

format:
	ruff check --fix .
	black .

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache **/__pycache__

build:
	python -m build

publish-check:
	python -m twine check dist/*