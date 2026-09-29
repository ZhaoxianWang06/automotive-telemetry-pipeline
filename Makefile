.PHONY: build test pipeline sim analyze

build:
	docker compose build

test:
	docker compose run --rm --no-deps thermal_diagnostics pytest -q

sim:
	docker compose run --rm thermal_middleware

analyze:
	docker compose run --rm --no-deps thermal_diagnostics

pipeline:
	docker compose run --rm thermal_middleware
	docker compose run --rm --no-deps thermal_diagnostics
