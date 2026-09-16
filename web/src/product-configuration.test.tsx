// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  activateProductConfiguration: vi.fn(),
  deleteReference: vi.fn(),
  importProductConfiguration: vi.fn(),
  listProductConfigurations: vi.fn(),
  listProductVersionHistory: vi.fn(),
  listReferences: vi.fn(),
  previewProductConfiguration: vi.fn(),
  uploadReference: vi.fn(),
  validateProductConfiguration: vi.fn(),
}));

import {
  activateProductConfiguration,
  listProductConfigurations,
  listProductVersionHistory,
  listReferences,
} from "./api";
import { ProductConfiguration } from "./product-configuration";
import "./test-setup";
import type {
  ProductConfigurationItem,
  ProductVersionHistoryItem,
} from "./types";

const PRODUCT: ProductConfigurationItem = {
  product_code: "motor-private-car",
  title: "Fictional Private-Car Motor",
  family: "motor",
  status: "active",
  active_version: "v1",
};

const HISTORY: ProductVersionHistoryItem[] = [
  {
    version: "v1",
    status: "active",
    content_hash: "hash-v1",
    activated_at: null,
  },
  {
    version: "v2",
    status: "draft",
    content_hash: "hash-v2",
    activated_at: null,
  },
];

// Reset the mocked client before each screen check.
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listProductConfigurations).mockResolvedValue([PRODUCT]);
  vi.mocked(listProductVersionHistory).mockResolvedValue(HISTORY);
  vi.mocked(listReferences).mockResolvedValue([]);
});

// Verify the administrator screen agrees with the API before it activates.
describe("product activation", () => {
  it("lists the configured product and its version history", async () => {
    render(<ProductConfiguration token="session" />);

    expect(await screen.findByText("Fictional Private-Car Motor")).toBeTruthy();
    expect(await screen.findByText(/Active version: v1/)).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Activate" })).toHaveLength(1);
  });

  it("asks for confirmation before activating a draft", async () => {
    render(<ProductConfiguration token="session" />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Activate" }));

    expect(
      screen.getByRole("heading", { name: "Activate this version?" }),
    ).toBeTruthy();
    expect(activateProductConfiguration).not.toHaveBeenCalled();
  });

  it("activates the confirmed version and reloads the history", async () => {
    vi.mocked(activateProductConfiguration).mockResolvedValue({
      product_code: "motor-private-car",
      version: "v2",
      status: "active",
    });
    render(<ProductConfiguration token="session" />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Activate" }));
    await user.click(screen.getByRole("button", { name: "Activate version" }));

    await waitFor(() =>
      expect(activateProductConfiguration).toHaveBeenCalledWith(
        "session",
        "motor-private-car",
        "v2",
      ),
    );
    expect(listProductVersionHistory).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("leaves the version alone when cancelled", async () => {
    render(<ProductConfiguration token="session" />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Activate" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(activateProductConfiguration).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
