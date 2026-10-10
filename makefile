.PHONY: run test

run:
	poetry run python src/price_parser/parser.py

test:
	poetry run pytest -v

lint:
	poetry run ruff check .

fix:
	poetry run ruff check --fix .
	poetry run ruff format .

.PHONY: run test lint fix typecheck format-check
typecheck:
	poetry run mypy

format-check:
	poetry run ruff format --check .