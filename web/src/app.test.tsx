// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 500;
  },
  activateProductConfiguration: vi.fn(),
  completeCase: vi.fn(),
  createSession: vi.fn(),
  deleteReference: vi.fn(),
  importProductConfiguration: vi.fn(),
  listAudit: vi.fn(),
  listCases: vi.fn(),
  listCatalog: vi.fn(),
  listDocuments: vi.fn(),
  listProductConfigurations: vi.fn(),
  listProductVersionHistory: vi.fn(),
  listQueue: vi.fn(),
  listReferences: vi.fn(),
  previewProductConfiguration: vi.fn(),
  readCase: vi.fn(),
  readCaseConfiguration: vi.fn(),
  readSession: vi.fn(),
  removeDocument: vi.fn(),
  resubmitCase: vi.fn(),
  runEvaluation: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
  startReview: vi.fn(),
  submitCase: vi.fn(),
  submitReview: vi.fn(),
  uploadDocument: vi.fn(),
  uploadReference: vi.fn(),
  validateProductConfiguration: vi.fn(),
}));

import {
  createSession,
  listAudit,
  listCases,
  listCatalog,
  listDocuments,
  listQueue,
  readCaseConfiguration,
  readSession,
} from "./api";
import { App } from "./app";
import "./test-setup";
import type {
  AuditEvent,
  CaseConfiguration,
  CaseRecord,
  ProductCatalogItem,
  QueueItem,
} from "./types";

const ACTIVE_CATALOGUE: ProductCatalogItem = {
  product_code: "motor-private-car",
  title: "Fictional Private-Car Motor",
  family: "motor",
  scope: "Fictional demonstration only",
  description: "Synthetic demonstration product",
  version: "v2",
  fields: [],
  documents: [
    {
      code: "identity_record",
      title: "Active catalogue identity record",
      requirement: "required",
      accepted_types: ["application/pdf"],
    },
  ],
};

const PINNED_CASE: CaseRecord = {
  id: "case-id",
  product_code: "motor-private-car",
  product_version: "v1",
  rulebook_version: "v1",
  status: "new",
};

const PINNED_CONFIGURATION: CaseConfiguration = {
  case_id: "case-id",
  product_code: "motor-private-car",
  product_version: "v1",
  rulebook_version: "v1",
  fields: [],
  documents: [
    {
      code: "identity_record",
      title: "Pinned version identity record",
      requirement: "required",
      required: true,
      accepted_types: ["application/pdf"],
      condition: null,
    },
  ],
};

const REVIEW_ITEM: QueueItem = {
  case_id: "00000000-0000-0000-0000-000000000001",
  product_code: "motor-private-car",
  status: "underwriter_review",
  route: "standard",
  selected_route: null,
  specialist_label: null,
  specialist: false,
  awaiting_handoff: false,
};

const AUDIT_EVENT: AuditEvent = {
  id: "audit-id",
  actor_user_id: "administrator-id",
  event_type: "case_created",
  details: { status: "new" },
  occurred_at: "2026-09-16T08:00:00Z",
};

// Sign in as the demo applicant through the rendered role entry screen.
async function signIn() {
  const user = userEvent.setup();
  await user.type(
    screen.getByLabelText("Email"),
    "applicant@synthetic.test",
  );
  await user.type(
    screen.getByLabelText("Password"),
    "underwriteflow-demo-applicant",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  return user;
}

// Sign in as the demo administrator through the rendered role entry screen.
async function signInAsAdministrator() {
  const user = userEvent.setup();
  await user.type(
    screen.getByLabelText("Email"),
    "administrator@synthetic.test",
  );
  await user.type(
    screen.getByLabelText("Password"),
    "underwriteflow-demo-administrator",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  return user;
}

// Reset the mocked client and default every call to an empty result.
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listCatalog).mockResolvedValue([]);
  vi.mocked(listCases).mockResolvedValue([]);
  vi.mocked(listDocuments).mockResolvedValue([]);
  vi.mocked(listQueue).mockResolvedValue([]);
  vi.mocked(listAudit).mockResolvedValue([]);
});

// Verify administrators can open a queue row in the audit workspace.
describe("administrator queue inspection", () => {
  it("opens the selected case audit history", async () => {
    vi.mocked(createSession).mockResolvedValue({
      token: "session",
      expires_in: 900,
    });
    vi.mocked(readSession).mockResolvedValue({
      sub: "administrator-id",
      role: "Administrator",
    });
    vi.mocked(listQueue).mockImplementation(async (_token, status) =>
      status === "underwriter_review" ? [REVIEW_ITEM] : [],
    );
    vi.mocked(listAudit).mockResolvedValue([AUDIT_EVENT]);

    render(<App />);
    const user = await signInAsAdministrator();

    await user.click(
      await screen.findByRole("button", { name: "Open all queues" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "View audit" }),
    );

    await waitFor(() =>
      expect(listAudit).toHaveBeenCalledWith(
        "session",
        REVIEW_ITEM.case_id,
      ),
    );
    expect(await screen.findByText("case created")).toBeTruthy();
  });
});

// Verify a restored case keeps the version it was pinned to.
describe("applicant document requirements", () => {
  it("shows the pinned version instead of the active catalogue", async () => {
    vi.mocked(createSession).mockResolvedValue({
      token: "session",
      expires_in: 900,
    });
    vi.mocked(readSession).mockResolvedValue({
      sub: "applicant-id",
      role: "Applicant",
    });
    vi.mocked(listCatalog).mockResolvedValue([ACTIVE_CATALOGUE]);
    vi.mocked(listCases).mockResolvedValue([PINNED_CASE]);
    vi.mocked(readCaseConfiguration).mockResolvedValue(PINNED_CONFIGURATION);

    render(<App />);
    const user = await signIn();

    await waitFor(() =>
      expect(readCaseConfiguration).toHaveBeenCalledWith(
        "session",
        "case-id",
      ),
    );
    await user.click(
      (await screen.findAllByRole("button", { name: "Open documents" }))[0],
    );

    expect(
      await screen.findByText("Pinned version identity record"),
    ).toBeTruthy();
    expect(screen.queryByText("Active catalogue identity record")).toBeNull();
  });

  it("still opens documents when no version is active", async () => {
    vi.mocked(createSession).mockResolvedValue({
      token: "session",
      expires_in: 900,
    });
    vi.mocked(readSession).mockResolvedValue({
      sub: "applicant-id",
      role: "Applicant",
    });
    vi.mocked(listCatalog).mockResolvedValue([]);
    vi.mocked(listCases).mockResolvedValue([PINNED_CASE]);
    vi.mocked(readCaseConfiguration).mockResolvedValue(PINNED_CONFIGURATION);

    render(<App />);
    const user = await signIn();

    await user.click(
      (await screen.findAllByRole("button", { name: "Open documents" }))[0],
    );

    expect(
      await screen.findByRole("heading", { name: "Add your documents." }),
    ).toBeTruthy();
  });
});
