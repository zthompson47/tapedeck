.PHONY: help test clean lint

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"

test:
	python -m pytest

clean:
	find . -name '*.pyc' -exec rm -rf {} \;

lint:
	python -m pylint tests tapedeck
	python -m flake8 tests tapedeck
