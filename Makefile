install:
	pip install -e .

install-dev:
	pip install -e .[dev]

install-lock:
	pip install -r requirements.txt

run:
	export DISCORD_TOKEN_FILE=secrets/discord_token; \
	PYTHONPATH=src python -m aergogen

format:
	isort --profile black . && black .

check-format:
	isort --profile black --check . && black --check .

check-types:
	mypy --check-untyped-defs .

test:
	pytest tests

lock:
	pip-compile --verbose --upgrade --output-file requirements.txt pyproject.toml

clean:
	git clean -Xdf
