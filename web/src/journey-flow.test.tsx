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
  setUnauthorizedHandler: vi.fn(),
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
} from "./api";
import { App } from "./app";
import "./test-setup";
import type { ProductCatalogItem } from "./types";

const MOTOR: ProductCatalogItem = {
  product_code: "motor-private-car",
  title: "Fictional Private-Car Motor",
  family: "motor",
  scope: "Fictional demonstration only",
  description: "Synthetic demonstration product",
  version: "v4",
  fields: [],
  documents: [],
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

beforeEach(() => {
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
    id,
    product_code: "motor-private-car",
    product_version: "v4",
    rulebook_version: "v1",
    status: "new",
    journey: "renewal",
  }));
  vi.mocked(listDocuments).mockResolvedValue([]);
  vi.mocked(readCaseConfiguration).mockResolvedValue({
    case_id: "case-id",
    product_code: "motor-private-car",
    product_version: "v4",
    rulebook_version: "v1",
    journey: "renewal",
    fields: [],
    documents: [],
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

  it("creates the case with the chosen journey", async () => {
    vi.mocked(createCase).mockResolvedValue({
      id: "case-id",
      product_code: "motor-private-car",
      product_version: "v4",
      rulebook_version: "v1",
      status: "new",
      journey: "renewal",
    });
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
    await user.click(
      screen.getByRole("button", { name: "Continue to documents" }),
    );

    await waitFor(() =>
      expect(createCase).toHaveBeenCalledWith(
        "session",
        expect.objectContaining({ journey: "renewal" }),
      ),
    );
  });
});
