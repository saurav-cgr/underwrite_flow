// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
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

// Move to the named section using the builder's own section navigation.
async function goToSection(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  await user.click(screen.getByRole("button", { name }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(previewProductConfiguration).mockImplementation(
    async (_token, yamlText) => JSON.parse(yamlText),
  );
});

describe("guided document authoring", () => {
  it(
    "captures a conditional document referencing an existing field, and "
      + "its required_for journeys",
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
      await user.type(screen.getByLabelText("Field key"), "vehicle_age");
      await user.type(screen.getByLabelText("Field label"), "Vehicle age");
      await user.click(screen.getByRole("button", { name: "Save field" }));

      await goToSection(user, "Documents");
      await user.click(screen.getByRole("button", { name: "Add document" }));
      await user.type(
        screen.getByLabelText("Document code"),
        "inspection_photo",
      );
      await user.type(
        screen.getByLabelText("Document title"),
        "Synthetic inspection photo",
      );
      await user.selectOptions(
        screen.getByLabelText("Requirement"),
        "conditional",
      );
      await user.selectOptions(
        screen.getByLabelText("Condition field"),
        "vehicle_age",
      );
      await user.selectOptions(
        screen.getByLabelText("Condition operator"),
        "greater_than",
      );
      await user.type(screen.getByLabelText("Condition value"), "12");
      await user.click(screen.getByLabelText("Required for renewal"));
      await user.click(screen.getByRole("button", { name: "Save document" }));

      await goToSection(user, "Specialist labels");
      await user.type(
        screen.getByLabelText("Specialist label"),
        "motor inspection",
      );
      await user.click(screen.getByRole("button", { name: "Add label" }));

      await goToSection(user, "Routing rules");
      await user.click(
        screen.getByRole("button", { name: "Add routing rule" }),
      );
      await user.type(screen.getByLabelText("Rule code"), "standard_review");
      await user.type(screen.getByLabelText("Comparison value"), "0");
      await user.click(
        screen.getByRole("button", { name: "Save routing rule" }),
      );

      await goToSection(user, "Review");
      await user.click(await screen.findByRole("button", { name: "Import" }));

      const [, sentText] =
        vi.mocked(importProductConfiguration).mock.calls[0];
      const sent = JSON.parse(sentText);
      const document = sent.documents.find(
        (item: { code: string }) => item.code === "inspection_photo",
      );

      expect(document.requirement).toBe("conditional");
      expect(document.condition).toEqual({
        field: "vehicle_age",
        operator: "greater_than",
        value: 12,
      });
      expect(document.required_for).toEqual(["renewal"]);
    },
  );
});
