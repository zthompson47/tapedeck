.PHONY: help test clean lint coverage

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"
	@echo "lint - check code for style and static errors"

test:
	python -m pytest

clean:
	find . -name '*.pyc' -exec rm {} +
	rm -f .coverage
	rm -f .coverage.*
	rm -rf htmlcov/*

lint:
	python -m flake8 tapedeck tests
	python -m mypy -m tapedeck
	python -m pycodestyle tapedeck tests
	python -m pydocstyle tapedeck tests
	python -m pyflakes tapedeck tests
	python -m pylint tapedeck tests

coverage: clean
	coverage run --module pytest
	coverage combine
	coverage report -m

fulltest: coverage lint
