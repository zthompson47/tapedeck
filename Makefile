.PHONY: help test clean

help:
	@echo "test - run pytest"
	@echo "clean - remove build and runtime files"

test:
	pytest

clean:
	find . -name '*.pyc' -exec rm -rf {} \;
