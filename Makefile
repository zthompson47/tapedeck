.PHONY: help test clean-tools clean-coverage clean-dist \
	    clean lint coverage testall dist

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
	rm -rf tapedeck.egg-info/

other_files = sitecustomize.py setup.py
lint:
	python -m flake8 tapedeck tests $(other_files)
	python -m mypy tapedeck $(other_files)
	pytype tapedeck $(other_files)
	python -m pydocstyle tapedeck tests $(other_files)
	python -m pylint tapedeck tests $(other_files)

coverage: clean-coverage
	coverage run --module pytest
	coverage combine
	coverage report -m
	coverage html

testall: coverage lint

dist: clean-dist
	python setup.py sdist bdist_wheel
