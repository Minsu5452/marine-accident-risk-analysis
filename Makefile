.PHONY: test lint typecheck clean-report coverage collect

test:
	uv run pytest
lint:
	uv run ruff check .
typecheck:
	uv run mypy
clean-report:
	uv run python scripts/clean_accidents.py
coverage:
	uv run python scripts/station_coverage.py
collect:
	uv run python scripts/collect_weather.py --start $(START) --end $(END)
