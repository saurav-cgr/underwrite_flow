# Documentation Model: README Operation Guidance

This feature adds no application data model or persisted records. Its
documentation concepts are below.

### Environment mode

Name, intended use, provider, isolation, and restriction. Give one example each
for development, evaluation, and production, matching existing configuration.

### Gemini setup

Provider selection, fields, acknowledgement, and secret handling. Name no
secret value and retain a fake-provider alternative.

### Local reset

Scope, warning, stop, remove, restart, and verify steps. Name only development
database and upload state; do not use broad volume deletion.

### Workflow flow

Parent graph, fan-out, product path, reconciliation, recommendation, interrupt,
resume, and completion. Distinguish parallel and sequential work, checkpoint
support, audit source, and human authority.

## State relation

```text
local persisted state
  -> explicit reset warning
  -> stopped development stack
  -> database + uploads removed
  -> bootstrap on startup
  -> empty fictional baseline verified
```

The reset is intentionally one-way. It is not an audit correction, migration,
or production recovery procedure.
