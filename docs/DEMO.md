# UnderwriteFlow demo guide

This flow is designed for a three-to-five-minute portfolio demonstration.
Use only the fictional accounts and data already in the repository.

## 1. Start the stack

```bash
cp .env.example .env
docker compose up --build
```

The bootstrap container applies the fresh-schema migration, provisions the
three demo roles, and imports the motor, life, and health configurations.

Before opening the applicant catalog, sign in as the fictional Administrator
and activate `motor-private-car` version `v1` through the product activation
API using that session's bearer token. Bootstrap imports configurations as
drafts; Administrator activation is required before applicants can see them.

## 2. Show the applicant journey

1. Open `http://localhost:5173` and choose Applicant.
2. Select the fictional private-car motor product.
3. Enter a young vehicle age, personal use, and zero fictional prior claims.
4. Upload synthetic PDF or image documents for identity and vehicle records.
5. Submit and show the case tracking state.

## 3. Show governed review

1. Open a second browser window and choose Underwriter.
2. Open the new case from the review queue.
3. Inspect the recommendation and evidence references.
4. Confirm the recommendation or override it with a reason.
5. Complete the case and show the completed queue state.

## 4. Show oversight and evaluation

1. Choose Administrator and open the audit workspace.
2. Search for the case UUID and inspect immutable event history.
3. Show the synthetic evaluation metrics and the 30-case holdout split.
4. Run `make smoke` to repeat the same flow with the fake provider.

## Demo boundaries

The recommendation is triage only. The application does not approve,
decline, bind, price, issue, renew, or cancel insurance. The product files,
uploaded documents, and evaluation cases are fictional demonstration data.
