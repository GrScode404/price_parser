.PHONY: run test

run:
	python src/price_parser/parser.py

test:
	pytest