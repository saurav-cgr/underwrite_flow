// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 500;
  },
  createCase: vi.fn(),
  createSession: vi.fn(),
  listCases: vi.fn(),
  listCatalog: vi.fn(),
  listDocuments: vi.fn(),
  readCase: vi.fn(),
  readCaseConfiguration: vi.fn(),
  readSession: vi.fn(),
  removeDocument: vi.fn(),
  resubmitCase: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
  submitCase: vi.fn(),
  updateApplication: vi.fn(),
  uploadDocument: vi.fn(),
}));

import {
  createCase,
  createSession,
  listCases,
  listCatalog,
  listDocuments,
  readCase,
  readCaseConfiguration,
  readSession,
  submitCase,
  updateApplication,
  uploadDocument,
} from "./api";
import { App } from "./app";
import "./test-setup";
import type {
  CaseConfiguration,
  DocumentRecord,
  ProductCatalogItem,
} from "./types";

const MOTOR: ProductCatalogItem = {
  product_code: "motor-private-car",
  title: "Fictional Private-Car Motor",
  family: "motor",
  scope: "Fictional demonstration only",
  description: "Synthetic demonstration product",
  version: "v4",
  fields: [
    {
      key: "vehicle_registration",
      label: "Vehicle registration",
      type: "text",
      required: true,
      help_text: "",
      validation: {},
      options: [],
    },
  ],
  documents: [
    {
      code: "previous_policy",
      title: "Previous policy",
      requirement: "required",
      accepted_types: ["application/pdf"],
      stage: "prior_policy",
    },
    {
      code: "rc_book",
      title: "RC book",
      requirement: "required",
      accepted_types: ["application/pdf"],
      stage: "supporting",
    },
  ],
  supported_journeys: ["new_business", "renewal"],
};

const TERM_LIFE: ProductCatalogItem = {
  product_code: "term-life-individual",
  title: "Fictional Individual Term Life",
  family: "life",
  scope: "Fictional demonstration only",
  description: "Synthetic demonstration product",
  version: "v1",
  fields: [],
  documents: [],
  supported_journeys: ["new_business"],
};

const MOTOR_CONFIGURATION: CaseConfiguration = {
  case_id: "case-id",
  product_code: "motor-private-car",
  product_version: "v4",
  rulebook_version: "v1",
  journey: "renewal",
  fields: MOTOR.fields,
  documents: MOTOR.documents.map((document) => ({
    code: document.code,
    title: document.title,
    requirement: document.requirement,
    required: document.requirement === "required",
    accepted_types: document.accepted_types,
    condition: null,
    stage: document.stage,
  })),
};

const RENEWAL_CASE = {
  id: "case-id",
  product_code: "motor-private-car",
  product_version: "v4",
  rulebook_version: "v1",
  status: "new",
  journey: "renewal" as const,
};

// Build safe stored-document metadata for one uploaded code.
function storedDocument(code: string): DocumentRecord {
  return {
    id: `doc-${code}`,
    document_code: code,
    filename: `${code}.pdf`,
    content_type: "application/pdf",
    byte_size: 1024,
    content_hash: "hash",
    page_count: 1,
  };
}

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

// Upload one synthetic file through its rendered document input.
async function uploadThrough(
  user: ReturnType<typeof userEvent.setup>,
  label: string,
) {
  const input = screen.getByLabelText(label) as HTMLInputElement;
  const file = new File(["synthetic"], "evidence.pdf", {
    type: "application/pdf",
  });
  await user.upload(input, file);
}

let uploadedDocuments: DocumentRecord[] = [];

beforeEach(() => {
  uploadedDocuments = [];
  vi.clearAllMocks();
  vi.mocked(listCases).mockResolvedValue([]);
  vi.mocked(createSession).mockResolvedValue({
    access_token: "session",
    refresh_token: "refresh",
    token_type: "bearer",
    expires_in: 900,
    refresh_expires_in: 28800,
  });
  vi.mocked(readSession).mockResolvedValue({
    id: "applicant-id",
    email: "applicant@synthetic.test",
    display_name: "Synthetic Applicant",
    role: { id: "role-applicant", code: "applicant" },
    permissions: ["cases:read", "cases:write"],
  });
  vi.mocked(listCatalog).mockImplementation(async (_token, journey) =>
    journey === "renewal" ? [MOTOR] : [MOTOR, TERM_LIFE],
  );
  vi.mocked(readCase).mockImplementation(async (_token, id) => ({
    ...RENEWAL_CASE,
    id,
  }));
  vi.mocked(listDocuments).mockImplementation(async () => [
    ...uploadedDocuments,
  ]);
  vi.mocked(uploadDocument).mockImplementation(async (_t, _id, code) => {
    const document = storedDocument(code);
    uploadedDocuments = [...uploadedDocuments, document];
    return document;
  });
  vi.mocked(readCaseConfiguration).mockResolvedValue(MOTOR_CONFIGURATION);
  vi.mocked(submitCase).mockResolvedValue({
    id: "case-id",
    status: "underwriter_review",
    recommendation: {},
  });
});

// Verify the journey choice is reachable and operable from the keyboard.
describe("journey choice", () => {
  it("selects a journey with the keyboard and loads its products", async () => {
    render(<App />);
    const user = await signIn();

    await user.click(
      screen.getByRole("button", { name: "Start an application" }),
    );
    const renewalOption = await screen.findByRole("radio", {
      name: /Renew a policy/,
    });
    renewalOption.focus();
    await user.keyboard("{Enter}");

    await waitFor(() =>
      expect(listCatalog).toHaveBeenCalledWith("session", "renewal"),
    );
    expect(
      await screen.findByText("Fictional Private-Car Motor"),
    ).toBeTruthy();
  });

  it(
    "excludes a product that does not support the chosen journey",
    async () => {
      render(<App />);
      const user = await signIn();

      await user.click(
        screen.getByRole("button", { name: "Start an application" }),
      );
      await user.click(
        await screen.findByRole("radio", { name: /Renew a policy/ }),
      );

      await screen.findByText("Fictional Private-Car Motor");
      expect(
        screen.queryByText("Fictional Individual Term Life"),
      ).toBeNull();
    },
  );

  it(
    "creates a draft renewal case as soon as a product is chosen",
    async () => {
      vi.mocked(createCase).mockResolvedValue(RENEWAL_CASE);
      render(<App />);
      const user = await signIn();

      await user.click(
        screen.getByRole("button", { name: "Start an application" }),
      );
      await user.click(
        await screen.findByRole("radio", { name: /Renew a policy/ }),
      );
      const productCard = (
        await screen.findByText("Fictional Private-Car Motor")
      ).closest("button");
      expect(productCard).not.toBeNull();
      await user.click(productCard as HTMLButtonElement);

      await waitFor(() =>
        expect(createCase).toHaveBeenCalledWith(
          "session",
          expect.objectContaining({ journey: "renewal", payload: {} }),
        ),
      );
      await screen.findByText("Upload your existing policy.");
    },
  );
});

// Verify a renewal walks prior policy, then the form, then evidence.
describe("staged renewal", () => {
  it("orders prior policy, the form, then supporting evidence", async () => {
    vi.mocked(createCase).mockResolvedValue(RENEWAL_CASE);
    vi.mocked(updateApplication).mockResolvedValue(RENEWAL_CASE);
    render(<App />);
    const user = await signIn();

    await user.click(
      screen.getByRole("button", { name: "Start an application" }),
    );
    await user.click(
      await screen.findByRole("radio", { name: /Renew a policy/ }),
    );
    const productCard = (
      await screen.findByText("Fictional Private-Car Motor")
    ).closest("button");
    await user.click(productCard as HTMLButtonElement);

    await screen.findByText("Upload your existing policy.");
    await uploadThrough(user, "Upload Previous policy");
    await user.click(
      await screen.findByRole("button", { name: "Continue to application" }),
    );

    await screen.findByText("Fictional Private-Car Motor");
    await user.type(
      screen.getByLabelText(/Vehicle registration/),
      "MH-01-AB-1234",
    );
    await user.click(
      screen.getByRole("button", { name: "Continue to documents" }),
    );

    await waitFor(() =>
      expect(updateApplication).toHaveBeenCalledWith(
        "session",
        "case-id",
        expect.objectContaining({
          payload: { vehicle_registration: "MH-01-AB-1234" },
        }),
      ),
    );
    expect(createCase).toHaveBeenCalledTimes(1);

    await screen.findByText("Add your documents.");
    await uploadThrough(user, "Upload RC book");
    await user.click(
      screen.getByRole("button", { name: "Submit for review" }),
    );

    await waitFor(() =>
      expect(submitCase).toHaveBeenCalledWith("session", "case-id"),
    );
  });

  it(
    "resumes an open renewal case after reload with its documents",
    async () => {
      uploadedDocuments = [storedDocument("previous_policy")];
      vi.mocked(listCases).mockResolvedValue([RENEWAL_CASE]);
      render(<App />);
      const user = await signIn();

      const openButtons = await screen.findAllByRole("button", {
        name: "Open documents",
      });
      await user.click(openButtons[0]);

      await screen.findByText("Upload your existing policy.");
      expect(await screen.findByText("previous_policy.pdf")).toBeTruthy();
      const continueButton = screen.getByRole("button", {
        name: "Continue to application",
      });
      expect(continueButton.hasAttribute("disabled")).toBe(false);
    },
  );
});
