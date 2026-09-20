// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
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

describe("guided editors", () => {
  it(
    "captures field options, operators, a specialist label, and a "
      + "two-document reconciliation check",
    async () => {
      vi.mocked(importProductConfiguration).mockResolvedValue({
        product_code: "motor-builder-demo",
        version: "v1",
        status: "draft",
      });
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

      await fillIdentity(user);

      await goToSection(user, "Applicant fields");
      await user.click(screen.getByRole("button", { name: "Add field" }));
      await user.type(screen.getByLabelText("Field key"), "coverage_tier");
      await user.type(screen.getByLabelText("Field label"), "Coverage tier");
      await user.selectOptions(
        screen.getByLabelText("Field type"),
        "enum",
      );
      await user.type(
        screen.getByLabelText("Options (comma separated)"),
        "basic, standard",
      );
      await user.click(screen.getByLabelText("Renewal"));
      await user.click(screen.getByRole("button", { name: "Save field" }));

      await goToSection(user, "Documents");
      await user.click(screen.getByRole("button", { name: "Add document" }));
      await user.type(
        screen.getByLabelText("Document code"),
        "identity_record",
      );
      await user.type(
        screen.getByLabelText("Document title"),
        "Synthetic identity record",
      );
      await user.click(screen.getByLabelText("image/jpeg"));
      await user.click(screen.getByRole("button", { name: "Save document" }));

      await goToSection(user, "Specialist labels");
      await addLabel(user);

      await goToSection(user, "Routing rules");
      await user.click(
        screen.getByRole("button", { name: "Add routing rule" }),
      );
      await user.type(
        screen.getByLabelText("Rule code"),
        "specialist_review",
      );
      await user.selectOptions(screen.getByLabelText("Operator"), "equals");
      await user.selectOptions(screen.getByLabelText("Route"), "specialist");
      await user.selectOptions(
        screen.getByLabelText("Specialist label"),
        "motor inspection",
      );
      await user.click(
        screen.getByRole("button", { name: "Save routing rule" }),
      );

      await goToSection(user, "Reconciliation");
      await user.click(
        screen.getByRole("button", { name: "Add reconciliation" }),
      );
      await user.type(
        screen.getByLabelText("Reconciliation code"),
        "motor_chassis_match",
      );
      await user.selectOptions(screen.getByLabelText("Kind"), "asset_match");
      await user.type(
        screen.getByLabelText("Document 1 code"),
        "vehicle_record",
      );
      await user.type(
        screen.getByLabelText("Document 1 field"),
        "chassis_number",
      );
      await user.type(
        screen.getByLabelText("Document 2 code"),
        "registration_certificate",
      );
      await user.type(
        screen.getByLabelText("Document 2 field"),
        "chassis_number",
      );
      await user.click(
        screen.getByRole("button", { name: "Save reconciliation" }),
      );

      await goToSection(user, "Review");
      await user.click(await screen.findByRole("button", { name: "Import" }));

      await waitFor(() =>
        expect(importProductConfiguration).toHaveBeenCalledTimes(1),
      );
      const [, sentText] =
        vi.mocked(importProductConfiguration).mock.calls[0];
      const sent = JSON.parse(sentText);

      const field = sent.fields.find(
        (item: { key: string }) => item.key === "coverage_tier",
      );
      expect(field.options).toEqual(["basic", "standard"]);
      expect(field.applies_to).toEqual(["new_business"]);

      const document = sent.documents.find(
        (item: { code: string }) => item.code === "identity_record",
      );
      expect(document.accepted_types).toContain("image/jpeg");

      const rule = sent.routing_rules.find(
        (item: { code: string }) => item.code === "specialist_review",
      );
      expect(rule.condition.operator).toBe("equals");
      expect(rule.specialist_label).toBe("motor inspection");

      const check = sent.reconciliations.find(
        (item: { code: string }) => item.code === "motor_chassis_match",
      );
      expect(check.inputs).toEqual({
        vehicle_record: "chassis_number",
        registration_certificate: "chassis_number",
      });
    },
  );
});

