.PHONY: run test

run:
	poetry run python src/price_parser/parser.py

test:
	poetry run pytest -v
