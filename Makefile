.PHONY: help test clean-cache clean-coverage clean lint coverage testall

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"
	@echo "lint - check code for style and static errors"
	@echo "coverage - measure how much code the tests cover"
	@echo "testall - shortcut for test/coverage/lint"

test:
	python -m pytest

clean-cache:
	find . -type d -name '__pycache__' -exec rm -r {} +
	find . -type d -name '.pytest_cache' -exec rm -r {} +

clean-coverage:
	rm -f .coverage
	rm -f .coverage.*
	rm -rf htmlcov/

clean: clean-coverage clean-cache
	rm -rf tapedeck.egg-info/

other_files = sitecustomize.py setup.py
lint:
	python -m flake8 tapedeck tests $(other_files)
	python -m mypy tapedeck $(other_files)
	python -m pycodestyle tapedeck tests $(other_files)
	python -m pydocstyle tapedeck tests $(other_files)
	python -m pyflakes tapedeck tests $(other_files)
	python -m pylint tapedeck tests $(other_files)

coverage: clean-coverage
	coverage run --module pytest
	coverage combine
	coverage report -m
	coverage html

testall: coverage lint
