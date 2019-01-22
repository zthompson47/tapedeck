.PHONY: help test clean-tools clean-coverage clean-dist \
	    clean lint coverage testall dist
project = tapedeck

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"
	@echo "lint - check code for style and static errors"
	@echo "coverage - measure how much code the tests cover"
	@echo "testall - shortcut for test/coverage/lint"

test:
	python -m pytest

clean-tools:
	find . -type d -name '.pytest_cache' -exec rm -r {} +
	find . -type d -name '.mypy_cache' -exec rm -r {} +
	find . -type d -name 'pytype_output' -exec rm -r {} +

clean-coverage:
	rm -f .coverage
	rm -f .coverage.*
	rm -rf htmlcov/

clean-dist:
	find . -type d -name '__pycache__' -exec rm -r {} +
	find . -type d -name 'build' -exec rm -r {} +
	find . -type d -name 'dist' -exec rm -r {} +

clean: clean-coverage clean-tools clean-dist
	rm -rf $(project).egg-info/

other_files = sitecustomize.py setup.py
lint:
	python -m flake8 --max-complexity 10 $(project) tests $(other_files)
	python -m flake8 $(project) tests $(other_files)
	python -m mypy $(project) $(other_files)
	pytype -d import-error,attribute-error $(project) $(other_files)
	python -m pydocstyle $(project) tests $(other_files)
	python -m pylint $(project) tests $(other_files)

coverage: clean-coverage
	coverage run --module pytest
	coverage combine
	coverage report -m
	coverage html

testall: coverage lint

dist: clean-dist
	python setup.py sdist bdist_wheel
