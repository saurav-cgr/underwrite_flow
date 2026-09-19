// @vitest-environment jsdom
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  importProductConfiguration: vi.fn(),
  previewProductConfiguration: vi.fn(),
}));

import { importProductConfiguration, previewProductConfiguration } from "./api";
import { ProductBuilder } from "./product-builder";
import "./test-setup";
import type { BuilderConfiguration } from "./product-builder-state";

const SECTIONS = [
  "Identity",
  "Journeys",
  "Applicant fields",
  "Documents",
  "Routing rules",
  "Reconciliation",
  "Specialist labels",
];

// Fill the identity section's required text inputs.
async function fillIdentity(user: ReturnType<typeof userEvent.setup>) {
  await user.type(
    screen.getByLabelText("Product code"),
    "motor-builder-demo",
  );
  await user.type(screen.getByLabelText("Title"), "Synthetic Builder Product");
  await user.type(
    screen.getByLabelText("Scope"),
    "Fictional demonstration only",
  );
  await user.type(
    screen.getByLabelText("Description"),
    "Synthetic builder configuration",
  );
  await user.type(screen.getByLabelText("Version"), "v1");
}

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

// Add one document requirement through the current section's inline form.
async function addDocument(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Add document" }));
  await user.type(screen.getByLabelText("Document code"), "identity_record");
  await user.type(
    screen.getByLabelText("Document title"),
    "Synthetic identity record",
  );
  await user.click(screen.getByRole("button", { name: "Save document" }));
}

// Add one routing rule through the current section's inline form.
async function addRule(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Add routing rule" }));
  await user.type(screen.getByLabelText("Rule code"), "standard_review");
  await user.type(screen.getByLabelText("Comparison value"), "0");
  await user.click(screen.getByRole("button", { name: "Save routing rule" }));
}

// Add one specialist label through the current section's inline form.
async function addLabel(user: ReturnType<typeof userEvent.setup>) {
  await user.type(
    screen.getByLabelText("Specialist label"),
    "motor inspection",
  );
  await user.click(screen.getByRole("button", { name: "Add label" }));
}

// Move to the named section using the builder's own section navigation.
async function goToSection(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  await user.click(screen.getByRole("button", { name }));
}

// Walk every required section and reach the review step, importing content.
async function completeBuilder(user: ReturnType<typeof userEvent.setup>) {
  await fillIdentity(user);
  await goToSection(user, "Journeys");
  await goToSection(user, "Applicant fields");
  await addField(user);
  await goToSection(user, "Documents");
  await addDocument(user);
  await goToSection(user, "Routing rules");
  await addRule(user);
  await goToSection(user, "Specialist labels");
  await addLabel(user);
  await goToSection(user, "Review");
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(previewProductConfiguration).mockImplementation(
    async (_token, yamlText) => JSON.parse(yamlText),
  );
});

describe("seven-section navigation", () => {
  it("labels every section and moves between them by keyboard", async () => {
    render(
      <ProductBuilder
        family="motor"
        onImported={vi.fn()}
        onStatus={vi.fn()}
        source="blank"
        token="session"
      />,
    );
    const user = userEvent.setup();

    for (const name of SECTIONS) {
      const button = screen.getByRole("button", { name });
      button.focus();
      await user.keyboard("{Enter}");
      expect(button.getAttribute("aria-current")).toBe("step");
      expect(
        screen.getByRole("heading", { name, level: 2 }),
      ).toBeTruthy();
    }
  });
});

describe("required-section validation", () => {
  it("focuses error summary linking to missing identity fields", async () => {
    render(
      <ProductBuilder
        family="motor"
        onImported={vi.fn()}
        onStatus={vi.fn()}
        source="blank"
        token="session"
      />,
    );
    const user = userEvent.setup();

    await goToSection(user, "Review");

    const summary = await screen.findByRole("alert");
    expect(summary.textContent).toMatch(/product code/i);
    await waitFor(() => expect(document.activeElement).toBe(summary));
  });
});

describe("import", () => {
  it("sends the normalized builder state as JSON text on import", async () => {
    vi.mocked(importProductConfiguration).mockResolvedValue({
      product_code: "motor-builder-demo",
      version: "v1",
      status: "draft",
    });
    const onImported = vi.fn();
    render(
      <ProductBuilder
        family="motor"
        onImported={onImported}
        onStatus={vi.fn()}
        source="blank"
        token="session"
      />,
    );
    const user = userEvent.setup();

    await completeBuilder(user);
    await user.click(await screen.findByRole("button", { name: "Import" }));

    await waitFor(() =>
      expect(importProductConfiguration).toHaveBeenCalledTimes(1),
    );
    const [, sentText] = vi.mocked(importProductConfiguration).mock.calls[0];
    const sent = JSON.parse(sentText);
    expect(sent.product_code).toBe("motor-builder-demo");
    expect(sent.fields[0].key).toBe("vehicle_age");
    await waitFor(() =>
      expect(onImported).toHaveBeenCalledWith("motor-builder-demo"),
    );
  });
});

describe("non-color diff against the active configuration", () => {
  it("marks an added field with text, not color alone", async () => {
    const active: BuilderConfiguration = {
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
      reconciliations: [],
      specialist_labels: ["motor inspection"],
    };
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
