.PHONY: help test clean-tools clean-coverage clean-dist \
	    clean lint coverage testall dist
project = tapedeck

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"
	@echo "lint - check code for style"
	@echo "coverage - measure how much code the tests cover"
	@echo "testall - shortcut for test/coverage/lint"

test:
	python -m pytest

clean-tools:
	find . -type d -name '.pytest_cache' -exec rm -r {} +
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

other_files = sitecustomize.py setup.py
disabled = 'wrong-import-order,\
		    no-value-for-parameter,\
		    unused-import,\
		    unused-argument,\
		    redefined-outer-name'
lint:
	python -m flake8 --max-complexity 10 $(project) tests $(other_files)
	python -m pydocstyle $(project) tests $(other_files)
	python -m pylint $(project)
	python -m pylint --disable=$(disabled) tests $(other_files)

coverage: clean-coverage
	coverage run --module pytest
	coverage combine
	coverage html
	coverage report -m

testall: lint coverage

dist: clean-dist
	python setup.py sdist bdist_wheel
