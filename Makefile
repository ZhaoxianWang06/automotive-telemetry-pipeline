.PHONY: build test pipeline sim analyze

build:
	docker compose build

test:
	docker compose run --rm --no-deps analyzer pytest -q

sim:
	docker compose run --rm simulator

analyze:
	docker compose run --rm --no-deps analyzer

pipeline:
	docker compose run --rm simulator
	docker compose run --rm --no-deps analyzer
