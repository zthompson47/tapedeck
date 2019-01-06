.PHONY: help test clean lint coverage

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"
	@echo "lint - check code for style and static errors"

test:
	python -m pytest

clean:
	find . -name '*.pyc' -exec rm {} +

lint:
	python -m flake8 tapedeck tests
	python -m mypy tapedeck tests
	python -m pycodestyle tapedeck tests
	python -m pydocstyle tapedeck tests
	python -m pyflakes tapedeck tests
	python -m pylint tapedeck tests

coverage:
	coverage run --source tapedeck --module pytest
	coverage report -m
