main:
	pipenv run python3 main.py

test:
	pipenv install --dev
	pipenv run python3 -m pytest *.py
