.PHONY: lint
lint:
	@ruff check

.PHONY: types
types:
	@mypy src/main.py --follow-untyped-imports

.PHONY: tests
tests:
	@uv run pytest

.PHONY: deploy
deploy:
	@fly deploy --ha=false