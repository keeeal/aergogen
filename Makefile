install:
	pip install -r requirements.txt

install-dev:
	pip install .[dev]

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
