.PHONY: test coverage mutate clean

test:
	pytest

coverage:
	pytest --cov --cov-branch --cov-report=html

lint:
	ruff check src tests

format:
	black src tests

clean:
	rm -rf \
		htmlcov \
		.coverage \
		cosmic.sqlite \
		cosmic-fast.sqlite \
		.ruff_cache \
		__pycache__ \
		**/__pycache__ \
		mutants \
		.mutmut-cache
