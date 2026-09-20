.PHONY: test-api test-web smoke probe evaluate-e2e

test-api:
	docker compose run --rm api sh -c 'pytest -q \
		--cov=underwriteflow.workflow.reconciliation --cov-branch \
		--cov-report=term-missing --cov-fail-under=100; \
		test $$? -eq 0 -o $$? -eq 5'

test-web:
	docker compose run --rm web npm test -- --run

smoke:
	docker compose -f compose.yaml -f compose.smoke.yaml up --build \
		--abort-on-container-exit --exit-code-from api api

probe:
	docker compose -f compose.yaml -f compose.smoke.yaml run --rm api \
		python /app/scripts/pilot_load_probe.py

evaluate-e2e:
	docker compose -f compose.evaluation.yaml down --remove-orphans
	docker compose -f compose.evaluation.yaml up -d --build evaluation-api
	docker compose -f compose.evaluation.yaml run --rm evaluation-runner; \
		code=$$?; \
		docker compose -f compose.evaluation.yaml down --remove-orphans; \
		exit $$code
