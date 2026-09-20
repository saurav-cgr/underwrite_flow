// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  importProductConfiguration: vi.fn(),
  previewProductConfiguration: vi.fn(),
  validateProductConfiguration: vi.fn(),
}));

import {
  ApiError,
  importProductConfiguration,
  previewProductConfiguration,
  validateProductConfiguration,
} from "./api";
import { ProductImport } from "./product-import";
import "./test-setup";
import type { BuilderConfigurationPreview } from "./product-builder-state";

const validateMock = vi.mocked(validateProductConfiguration);
const previewMock = vi.mocked(previewProductConfiguration);
const importMock = vi.mocked(importProductConfiguration);

const VALIDATED = {
  product_code: "motor-private-car",
  version: "v2",
  status: "draft",
};

const PREVIEW: BuilderConfigurationPreview = {
  product_code: "motor-private-car",
  title: "Fictional Private-Car Motor",
  family: "motor",
  scope: "Fictional demonstration only",
  description: "Synthetic demonstration product",
  version: "v2",
  status: "draft",
  fields: [],
  documents: [],
  routing_rules: [],
  supported_journeys: ["new_business"],
  field_count: 3,
  document_count: 5,
  routing_rule_count: 7,
  reconciliation_count: 1,
  reconciliations: [
    {
      code: "motor_ncb_match",
      kind: "ncb_match",
      inputs: {
        application: "claimed_ncb_percent",
        previous_policy: "ncb_percent",
      },
      applies_to: ["renewal"],
    },
  ],
  specialist_labels: ["motor inspection"],
};

// Render the import panel with synthetic status reporting.
function renderPanel() {
  const onImported = vi.fn().mockResolvedValue(undefined);
  const onHydrate = vi.fn();
  const onStatus = vi.fn();
  render(
    <ProductImport
      onHydrate={onHydrate}
      onImported={onImported}
      onStatus={onStatus}
      token="session"
    />,
  );
  return { onHydrate, onImported, onStatus };
}

// Locate the YAML field the administrator pastes into.
function yamlField() {
  return screen.getByRole("textbox", { name: /product configuration yaml/i });
}

// Reset the mocked client before each panel check.
beforeEach(() => {
  vi.clearAllMocks();
});

// Verify the panel validates, previews, and imports administrator YAML.
describe("product import panel", () => {
  it("loads a chosen file locally without contacting the API", async () => {
    const { onStatus } = renderPanel();
    const user = userEvent.setup();

    await user.upload(
      screen.getByLabelText(/choose product configuration yaml/i),
      new File(["product_code: motor-private-car"], "product.yaml", {
        type: "text/yaml",
      }),
    );

    await waitFor(() =>
      expect(onStatus).toHaveBeenCalledWith({
        notice: "YAML loaded locally. Validate it before importing.",
      }),
    );
    expect(validateMock).not.toHaveBeenCalled();
    expect((yamlField() as HTMLTextAreaElement).value).toBe(
      "product_code: motor-private-car",
    );
  });

  it("validates pasted YAML and reports the parsed identity", async () => {
    validateMock.mockResolvedValue(VALIDATED);
    const { onStatus } = renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Validate" }));

    expect(validateMock).toHaveBeenCalledWith(
      "session",
      "product_code: motor-private-car",
    );
    await waitFor(() =>
      expect(onStatus).toHaveBeenCalledWith({
        notice: "Configuration motor-private-car v2 is valid.",
      }),
    );
  });

  it("asks for YAML before it validates anything", async () => {
    const { onStatus } = renderPanel();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Validate" }));

    expect(onStatus).toHaveBeenCalledWith({
      message: "Paste or choose a YAML configuration first.",
    });
    expect(validateMock).not.toHaveBeenCalled();
  });

  it("previews the normalized counts of valid YAML", async () => {
    validateMock.mockResolvedValue(VALIDATED);
    previewMock.mockResolvedValue(PREVIEW);
    renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByText("Fields")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Documents")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
    expect(screen.getByText("Routing rules")).toBeTruthy();
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("Reconciliations")).toBeTruthy();
  });

  it("shows each configured reconciliation definition", async () => {
    previewMock.mockResolvedValue(PREVIEW);
    renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByText("motor_ncb_match")).toBeTruthy();
    expect(screen.getByText("No-claim bonus match")).toBeTruthy();
    expect(
      screen.getByText(
        "application → claimed_ncb_percent, previous_policy → ncb_percent",
      ),
    ).toBeTruthy();
  });

  it("says when a version configures no checks", async () => {
    previewMock.mockResolvedValue({
      ...PREVIEW,
      reconciliation_count: 0,
      reconciliations: [],
    });
    renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(
      await screen.findByText(
        "No reconciliation checks are configured for this version.",
      ),
    ).toBeTruthy();
  });

  it("hydrates the guided builder from the current preview", async () => {
    previewMock.mockResolvedValue(PREVIEW);
    const { onHydrate } = renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(
      await screen.findByRole("button", { name: "Edit in guided builder" }),
    );

    expect(onHydrate).toHaveBeenCalledWith(PREVIEW);
  });

  it("imports a draft and hands the product code upward", async () => {
    importMock.mockResolvedValue(VALIDATED);
    const { onImported, onStatus } = renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Import draft" }));

    await waitFor(() =>
      expect(onImported).toHaveBeenCalledWith("motor-private-car"),
    );
    expect(onStatus).toHaveBeenCalledWith({
      notice: "Draft v2 imported for motor-private-car.",
    });
  });

  it("surfaces the API message for a rejected action", async () => {
    validateMock.mockRejectedValue(
      new ApiError(422, "Configuration is invalid"),
    );
    const { onStatus } = renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() =>
      expect(onStatus).toHaveBeenCalledWith({
        message: "Configuration is invalid",
      }),
    );
  });

  it("names the failing reconciliation reference when refused", async () => {
    validateMock.mockRejectedValue(
      new ApiError(
        422,
        "Invalid product configuration: reconciliation motor_ncb_match: " +
          "unknown input sources ['inspection_photo']",
      ),
    );
    const { onStatus } = renderPanel();
    const user = userEvent.setup();

    await user.type(yamlField(), "product_code: motor-private-car");
    await user.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() =>
      expect(onStatus).toHaveBeenCalledWith({
        message:
          "Invalid product configuration: reconciliation " +
          "motor_ncb_match: unknown input sources ['inspection_photo']",
      }),
    );
  });
});
