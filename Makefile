.PHONY: help test clean lint coverage fulltest

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"
	@echo "lint - check code for style and static errors"
	@echo "coverage - measure how much code the tests cover"
	@echo "fulltest - shortcut for test/coverage/lint"

test:
	python -m pytest

clean:
	find . -name '*.pyc' -exec rm {} +
	rm -f .coverage
	rm -f .coverage.*
	rm -rf htmlcov/*

lint:
	python -m flake8 tapedeck tests
	python -m pycodestyle tapedeck tests
	python -m pydocstyle tapedeck tests
	python -m pyflakes tapedeck tests
	python -m pylint tapedeck tests

coverage: clean
	coverage run --module pytest
	coverage combine
	coverage report -m

fulltest: coverage lint
