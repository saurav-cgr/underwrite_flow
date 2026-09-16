// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 500;
  },
  listDocuments: vi.fn(),
  removeDocument: vi.fn(),
  resubmitCase: vi.fn(),
  submitCase: vi.fn(),
  uploadDocument: vi.fn(),
}));

import { listDocuments, resubmitCase, submitCase } from "./api";
import { DocumentsScreen } from "./documents";
import "./test-setup";
import type {
  CaseRecord,
  DocumentRecord,
  ProductCatalogItem,
} from "./types";

const listDocumentsMock = vi.mocked(listDocuments);
const submitCaseMock = vi.mocked(submitCase);
const resubmitCaseMock = vi.mocked(resubmitCase);

const PRODUCT: ProductCatalogItem = {
  product_code: "motor-private-car",
  title: "Fictional Private-Car Motor",
  family: "motor",
  scope: "Fictional demonstration only",
  description: "Synthetic demonstration product",
  version: "v1",
  fields: [],
  documents: [
    {
      code: "identity_record",
      title: "Synthetic identity record",
      requirement: "required",
      accepted_types: ["application/pdf"],
    },
    {
      code: "inspection_photo",
      title: "Synthetic inspection photo",
      requirement: "conditional",
      accepted_types: ["image/png"],
    },
  ],
};

const CASE: CaseRecord = {
  id: "case-id",
  product_code: "motor-private-car",
  product_version: "v1",
  rulebook_version: "v1",
  status: "new",
};

const UPLOADED: DocumentRecord = {
  id: "document-id",
  document_code: "identity_record",
  filename: "synthetic.pdf",
  content_type: "application/pdf",
  byte_size: 2048,
  content_hash: "synthetic",
  page_count: 1,
};

const SUBMITTED = {
  id: "case-id",
  status: "underwriter_review",
  recommendation: { route: "expedited", factors: [] },
};

// Render the documents screen with synthetic case and catalogue fixtures.
function renderScreen(
  caseRecord: CaseRecord,
  onNavigate = vi.fn(),
  onCaseChange = vi.fn(),
) {
  render(
    <DocumentsScreen
      caseRecord={caseRecord}
      onCaseChange={onCaseChange}
      onNavigate={onNavigate}
      product={PRODUCT}
      token="session"
    />,
  );
  return { onCaseChange, onNavigate };
}

// Reset the mocked client before each screen-level check.
beforeEach(() => {
  vi.clearAllMocks();
  listDocumentsMock.mockResolvedValue([]);
});

// Verify one case can only be submitted once its required evidence is stored.
describe("case submission", () => {
  it("submits a ready case and records the new status", async () => {
    listDocumentsMock.mockResolvedValue([UPLOADED]);
    submitCaseMock.mockResolvedValue(SUBMITTED);
    const { onCaseChange, onNavigate } = renderScreen(CASE);
    const user = userEvent.setup();

    const submit = await screen.findByRole("button", {
      name: "Submit for review",
    });
    expect((submit as HTMLButtonElement).disabled).toBe(false);
    await user.click(submit);

    expect(submitCaseMock).toHaveBeenCalledWith("session", "case-id");
    expect(onCaseChange).toHaveBeenCalledWith({
      ...CASE,
      status: "underwriter_review",
    });
    expect(onNavigate).toHaveBeenCalledWith("tracking");
  });

  it("blocks submission until the required document is stored", async () => {
    renderScreen(CASE);

    const submit = await screen.findByRole("button", {
      name: "Submit for review",
    });

    expect((submit as HTMLButtonElement).disabled).toBe(true);
    expect(submitCaseMock).not.toHaveBeenCalled();
  });

  it("ignores a second click while the decision is in flight", async () => {
    listDocumentsMock.mockResolvedValue([UPLOADED]);
    let settle: (value: typeof SUBMITTED) => void = () => undefined;
    submitCaseMock.mockImplementation(
      () => new Promise((resolve) => {
        settle = resolve;
      }),
    );
    renderScreen(CASE);
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: "Submit for review" }),
    );
    await user.click(screen.getByRole("button", { name: "Submitting…" }));

    expect(submitCaseMock).toHaveBeenCalledTimes(1);

    settle(SUBMITTED);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Submit for review" }),
      ).toBeTruthy(),
    );
  });
});

// Verify a returned case is resubmitted rather than submitted again.
describe("case resubmission", () => {
  it("resubmits a case returned for information", async () => {
    listDocumentsMock.mockResolvedValue([UPLOADED]);
    resubmitCaseMock.mockResolvedValue(SUBMITTED);
    const { onNavigate } = renderScreen({
      ...CASE,
      status: "needs_information",
    });
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: "Resubmit for review" }),
    );

    expect(resubmitCaseMock).toHaveBeenCalledWith("session", "case-id");
    expect(submitCaseMock).not.toHaveBeenCalled();
    expect(onNavigate).toHaveBeenCalledWith("tracking");
  });

  it("offers no intake action once an underwriter owns the case", async () => {
    renderScreen({ ...CASE, status: "underwriter_review" });

    await screen.findByRole("button", { name: "Continue to tracking" });
    expect(screen.queryByRole("button", { name: /submit/i })).toBeNull();
  });
});
