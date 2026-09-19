# Synthetic Pilot Probe

Measured on 18 September 2026 with `make probe` in the local Docker Compose
stack. The run used fresh fictional motor cases, product version `v3`, ten
worker threads, the deterministic fake provider, and tracing disabled.

These are local decision-support measurements, not production capacity or
hosted-provider claims.

| Measure | 10 cases | 100 cases |
| --- | ---: | ---: |
| Cohort elapsed | 1.20 s | 9.79 s |
| Ordinary interaction p95 | 237 ms | 206 ms |
| Review-ready p95 | 968 ms | 822 ms |
| Queue query p95 | 17 ms | 68 ms |
| Fake-provider latency p95 | 3.32 ms | 4.03 ms |
| Maximum active provider calls | 6 | 6 |
| Provider calls per case | 3 | 3 |
| Maximum checked-out DB connections | 10 | 10 |
| Base DB pool size | 5 | 5 |
| PostgreSQL bytes per case | 36,293 B | 36,281 B |
| Checkpoint bytes per case | 22,389 B | 22,378 B |
| Upload bytes per case | 2,195 B | 2,195 B |

Local OCR took a median `0.108 s/page` across three runs of one synthetic PNG.
The PostgreSQL total includes checkpoint rows. The pool safely used overflow
connections above its base size. Every case produced the expected expedited
triage recommendation, paused for human confirmation, and completed only after
the authenticated synthetic underwriter confirmed it.

The probe met the local plan thresholds: ordinary p95 below two seconds,
review-ready p95 below 60 seconds, and no case above the configured three
document branches. Restart persistence remains covered by the dedicated
checkpoint and audit integration tests; this probe does not restart services.
