// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    code: string;

    // Mirror the real constructor so messages survive into the UI.
    constructor(status: number, message: string, code = "http_error") {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
  listAudit: vi.fn(),
  listQueue: vi.fn(),
}));

// The workspace owns the audit reader; the child panels keep their own tests.
vi.mock("./access-admin", () => ({
  AccessAdministration: () => null,
}));

vi.mock("./evaluation-panel", () => ({
  EvaluationPanel: () => null,
}));

import { listAudit, listQueue } from "./api";
import { AdminWorkspace } from "./admin";
import "./test-setup";
import type { AuditEvent } from "./types";

const FIRST_EVENT_ID = "2f0f1c2a-0000-4000-8000-000000000001";
const SECOND_EVENT_ID = "2f0f1c2a-0000-4000-8000-000000000002";

const FIRST_EVENT: AuditEvent = {
  id: FIRST_EVENT_ID,
  case_id: "case-1",
  actor_user_id: "user-applicant",
  event_type: "case_submitted",
  occurred_at: "2026-09-17T10:00:00Z",
  supersedes_event_id: null,
  details: {
    review_cycle: 0,
    recommendation: "expedited",
    provider_calls: [
      {
        document_id: "document-1",
        document_code: "vehicle_record",
        provider: "fake",
        model: null,
        attempts: 1,
        prompt_tokens: null,
        completion_tokens: null,
        usage_unavailable: true,
        request_hash: "a".repeat(64),
        result_hash: "b".repeat(64),
        error_code: null,
      },
      {
        document_id: "document-2",
        document_code: "identity_record",
        provider: "gemini",
        model: "gemini-synthetic",
        attempts: 2,
        prompt_tokens: 120,
        completion_tokens: 30,
        usage_unavailable: false,
        request_hash: "c".repeat(64),
        result_hash: "d".repeat(64),
        error_code: null,
      },
    ],
  },
};

const SECOND_EVENT: AuditEvent = {
  id: SECOND_EVENT_ID,
  case_id: "case-1",
  actor_user_id: "user-applicant",
  event_type: "case_resubmitted",
  occurred_at: "2026-09-17T10:05:00Z",
  supersedes_event_id: FIRST_EVENT_ID,
  details: { review_cycle: 1, recommendation: "needs_information" },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listQueue).mockResolvedValue([]);
  vi.mocked(listAudit).mockResolvedValue([]);
});

// Render the administrator workspace for one synthetic case identifier.
function renderWorkspace() {
  return render(
    <AdminWorkspace
      token="session"
      onNavigate={() => undefined}
      initialCaseId="case-1"
    />,
  );
}

// Read the rendered audit chronology items in timeline order.
async function auditItems() {
  const timeline = await screen.findByRole("list", {
    name: /audit chronology/i,
  });
  return within(timeline).getAllByRole("listitem");
}

// Verify audit history renders as an anchored, ordered chronology.
describe("audit chronology", () => {
  it("renders an anchored timeline in the returned order", async () => {
    vi.mocked(listAudit).mockResolvedValue([FIRST_EVENT, SECOND_EVENT]);
    renderWorkspace();

    const items = await auditItems();
    expect(items).toHaveLength(2);
    expect(items[0]?.id).toBe(`event-${FIRST_EVENT_ID}`);
    expect(items[1]?.id).toBe(`event-${SECOND_EVENT_ID}`);
    expect(within(items[0]!).getByText("Case submitted")).toBeTruthy();
    expect(within(items[1]!).getByText("Case resubmitted")).toBeTruthy();
    expect(vi.mocked(listAudit)).toHaveBeenCalledWith("session", "case-1");
  });

  it("links each event to the event it supersedes", async () => {
    vi.mocked(listAudit).mockResolvedValue([FIRST_EVENT, SECOND_EVENT]);
    renderWorkspace();

    const items = await auditItems();
    expect(
      within(items[0]!).queryByRole("link", { name: /supersedes/i }),
    ).toBeNull();
    const link = within(items[1]!).getByRole("link", {
      name: /supersedes: case submitted/i,
    });
    expect(link.getAttribute("href")).toBe(`#event-${FIRST_EVENT_ID}`);
  });

  it("reports provider usage and its unavailable marker", async () => {
    vi.mocked(listAudit).mockResolvedValue([FIRST_EVENT]);
    renderWorkspace();

    const item = (await auditItems())[0]!;
    expect(
      within(item).getByText("fake · 1 attempt · usage unavailable"),
    ).toBeTruthy();
    expect(
      within(item).getByText(
        "gemini · model gemini-synthetic · 2 attempts · "
          + "120 prompt tokens · 30 completion tokens",
      ),
    ).toBeTruthy();
  });
});
