// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 500;
  },
  createCase: vi.fn(),
  updateApplication: vi.fn(),
}));

import { ApplicationForm } from "./application-form";
import "./test-setup";
import type { ProductCatalogItem } from "./types";

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
  documents: [],
  supported_journeys: ["new_business", "renewal"],
};

// Verify a restored draft's stored answers prefill the rendered form.
describe("application form prefill", () => {
  it("prefills a field from initialValues", () => {
    render(
      <ApplicationForm
        product={MOTOR}
        journey="renewal"
        token="session"
        initialValues={{ vehicle_registration: "MH12AB1234" }}
        onCreated={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );

    const input = screen.getByLabelText(
      /Vehicle registration/,
    ) as HTMLInputElement;
    expect(input.value).toBe("MH12AB1234");
  });
});
