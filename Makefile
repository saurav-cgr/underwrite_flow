.PHONY: test-api test-web smoke

test-api:
	docker compose run --rm api sh -c 'pytest -q; test $$? -eq 0 -o $$? -eq 5'

test-web:
	docker compose run --rm web npm test -- --run

smoke:
	docker compose -f compose.yaml -f compose.smoke.yaml up --build --abort-on-container-exit --exit-code-from api api
