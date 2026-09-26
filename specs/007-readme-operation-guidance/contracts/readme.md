# README Content Contract

## Environment paths

The README must present three labeled, copyable paths:

- **development**: Normal local, fictional demonstration; the example selects
  the fake provider.
- **evaluation**: Isolated synthetic evaluation with no shared development
  state.
- **production**: Guard only; evaluation loading is refused and no readiness
  claim is made.

## Gemini path

The Gemini subsection must direct readers to `.env.example`, identify required
existing configuration fields and approval acknowledgment, and never show a
credential value. It must say that only approved redacted synthetic task data
may leave the local boundary. The fake-provider path remains credential-free.

## Reset path

The reset subsection must state, before its command, that it permanently
removes the local database and uploaded synthetic files. It must scope removal
to the two named development data volumes, avoid `docker compose down -v`, and
state that restarting reruns migrations and product bootstrap. It must say the
result has fictional accounts and product versions but no prior case, document,
review, or audit records.

## Workflow visual

The architecture visual and nearby text must show:

1. parent workflow and bounded document fan-out;
2. one selected product path and sequential deterministic reconciliation;
3. recommendation followed by human interrupt and authenticated resume; and
4. idempotent handoff/completion, checkpoint resume support, and immutable
   business audit history.
