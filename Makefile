.PHONY: test-api test-web smoke probe

test-api:
	docker compose run --rm api sh -c 'pytest -q; test $$? -eq 0 -o $$? -eq 5'

test-web:
	docker compose run --rm web npm test -- --run

smoke:
	docker compose -f compose.yaml -f compose.smoke.yaml up --build \
		--abort-on-container-exit --exit-code-from api api

probe:
	docker compose -f compose.yaml -f compose.smoke.yaml run --rm api \
		python /app/scripts/pilot_load_probe.py
