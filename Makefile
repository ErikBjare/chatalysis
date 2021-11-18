main:
	poetry run python3 main.py

test:
	poetry run python3 -m pytest

typecheck:
	poetry run mypy chatalysis/*.py --ignore-missing-imports
