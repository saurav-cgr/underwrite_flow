// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  importProductConfiguration: vi.fn(),
  previewProductConfiguration: vi.fn(),
}));

import { previewProductConfiguration } from "./api";
import { ProductBuilder } from "./product-builder";
import "./test-setup";
import type { BuilderConfiguration } from "./product-builder-state";

// Add one applicant field through the current section's inline form.
async function addField(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Add field" }));
  await user.type(screen.getByLabelText("Field key"), "vehicle_age");
  await user.type(screen.getByLabelText("Field label"), "Vehicle age");
  await user.type(
    screen.getByLabelText("Help text"),
    "Enter a fictional vehicle age.",
  );
  await user.click(screen.getByRole("button", { name: "Save field" }));
}

// Move to the named section using the builder's own section navigation.
async function goToSection(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  await user.click(screen.getByRole("button", { name }));
}

// Build one minimal active configuration a clone starts from.
function activeConfiguration(
  overrides: Partial<BuilderConfiguration> = {},
): BuilderConfiguration {
  return {
    product_code: "motor-builder-demo",
    title: "Synthetic Builder Product",
    family: "motor",
    scope: "Fictional demonstration only",
    description: "Synthetic builder configuration",
    version: "v1",
    status: "active",
    supported_journeys: ["new_business", "renewal"],
    fields: [],
    documents: [],
    routing_rules: [],
    reconciliations: [],
    specialist_labels: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(previewProductConfiguration).mockImplementation(
    async (_token, yamlText) => JSON.parse(yamlText),
  );
});

describe("non-color diff against the active configuration", () => {
  it("marks an added field with text, not color alone", async () => {
    const active = activeConfiguration({
      documents: [
        {
          code: "identity_record",
          title: "Synthetic identity record",
          requirement: "required",
          accepted_types: ["application/pdf"],
          stage: "supporting",
          applies_to: ["new_business", "renewal"],
        },
      ],
      routing_rules: [
        {
          code: "standard_review",
          condition: {
            field: "vehicle_age",
            operator: "greater_than",
            value: 0,
          },
          route: "standard",
          applies_to: ["new_business", "renewal"],
        },
      ],
      specialist_labels: ["motor inspection"],
    });
    render(
      <ProductBuilder
        activeConfiguration={active}
        family="motor"
        onImported={vi.fn()}
        onStatus={vi.fn()}
        source="clone"
        token="session"
      />,
    );
    const user = userEvent.setup();

    await goToSection(user, "Identity");
    const versionInput = screen.getByLabelText("Version");
    await user.clear(versionInput);
    await user.type(versionInput, "v2");
    await goToSection(user, "Applicant fields");
    await addField(user);
    await goToSection(user, "Review");

    const diff = await screen.findByRole("list", {
      name: "Configuration changes",
    });
    const added = within(diff).getByText(/^Added: fields\.vehicle_age$/);
    expect(added).toBeTruthy();
  });
});

describe("clone identity lock", () => {
  it("blocks review until the clone gets a distinct version", async () => {
    render(
      <ProductBuilder
        activeConfiguration={activeConfiguration()}
        family="motor"
        onImported={vi.fn()}
        onStatus={vi.fn()}
        source="clone"
        token="session"
      />,
    );
    const user = userEvent.setup();

    await goToSection(user, "Review");

    const summary = await screen.findByRole("alert");
    expect(summary.textContent).toMatch(
      /version distinct from the cloned source/i,
    );
  });

  it("keeps the cloned product code locked from editing", async () => {
    render(
      <ProductBuilder
        activeConfiguration={activeConfiguration()}
        family="motor"
        onImported={vi.fn()}
        onStatus={vi.fn()}
        source="clone"
        token="session"
      />,
    );

    expect(
      (screen.getByLabelText("Product code") as HTMLInputElement).disabled,
    ).toBe(true);
  });
});
