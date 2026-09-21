.PHONY: test-api test-web smoke probe evaluate-e2e load-evaluation-data \
	load-evaluation-data-eval

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

# Explicit operator command. Nothing loads evaluation data automatically.
# Requires EVALUATION_LOADER_ACTOR_TOKEN: a real access token for a user
# whose current authorization holds the `evaluation:run` permission.
load-evaluation-data:
	docker compose run --rm -e EVALUATION_LOADER_ACTOR_TOKEN api \
		python /app/scripts/load_evaluation_data.py

# Loads into the isolated evaluation stack instead of development. Requires
# EVALUATION_LOADER_ACTOR_TOKEN: a real access token minted by the
# evaluation stack's own login endpoint, scoped to its issuer and audience,
# for a user whose current authorization holds `evaluation:run`.
load-evaluation-data-eval:
	docker compose -f compose.evaluation.yaml run --rm \
		-e EVALUATION_LOADER_ACTOR_TOKEN evaluation-api \
		python /app/scripts/load_evaluation_data.py
