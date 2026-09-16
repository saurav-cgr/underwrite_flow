// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 422;
  },
  deleteReference: vi.fn(),
  listReferences: vi.fn(),
  uploadReference: vi.fn(),
}));

import { deleteReference, listReferences, uploadReference } from "./api";
import { ReferenceDocuments } from "./reference-documents";
import "./test-setup";
import type { ProductVersionHistoryItem, ReferenceDocument } from "./types";

const VERSIONS: ProductVersionHistoryItem[] = [
  {
    version: "v2",
    status: "draft",
    content_hash: "hash-v2",
    activated_at: null,
  },
  {
    version: "v1",
    status: "active",
    content_hash: "hash-v1",
    activated_at: null,
  },
];

const STORED: ReferenceDocument = {
  id: "reference-id",
  version: "v2",
  filename: "synthetic-reference.pdf",
  content_type: "application/pdf",
  byte_size: 4096,
  content_hash: "37a1c0d2f5",
  page_count: 2,
};

const listReferencesMock = vi.mocked(listReferences);
const uploadReferenceMock = vi.mocked(uploadReference);
const deleteReferenceMock = vi.mocked(deleteReference);

// Render the panel for one selected product.
function renderPanel(productCode: string | null = "motor-private-car") {
  render(
    <ReferenceDocuments
      productCode={productCode}
      token="session"
      versions={VERSIONS}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  listReferencesMock.mockResolvedValue([]);
});

// Verify the administrator can see the references stored for a version.
describe("reference document listing", () => {
  it("loads the references of the default version", async () => {
    listReferencesMock.mockResolvedValue([STORED]);
    renderPanel();

    expect(
      await screen.findByText("synthetic-reference.pdf"),
    ).toBeTruthy();
    expect(listReferencesMock).toHaveBeenCalledWith(
      "session",
      "motor-private-car",
      "v2",
    );
    expect(screen.getByText("4 KB · application/pdf")).toBeTruthy();
    expect(screen.getByText("2 pages")).toBeTruthy();
  });

  it("states plainly when a version has no reference", async () => {
    renderPanel();

    expect(
      await screen.findByText(
        "No reference document is stored for this version.",
      ),
    ).toBeTruthy();
  });

  it("asks for a product before offering any action", async () => {
    renderPanel(null);

    expect(
      await screen.findByText("Choose a product"),
    ).toBeTruthy();
    expect(listReferencesMock).not.toHaveBeenCalled();
  });
});

// Verify the administrator can attach a reference to the chosen version.
describe("reference document upload", () => {
  it("uploads the chosen file against the selected version", async () => {
    uploadReferenceMock.mockResolvedValue(STORED);
    renderPanel();
    const user = userEvent.setup();
    const file = new File(["synthetic"], "synthetic-reference.pdf", {
      type: "application/pdf",
    });

    await user.upload(
      screen.getByLabelText("Choose reference document"),
      file,
    );

    await waitFor(() =>
      expect(uploadReferenceMock).toHaveBeenCalledWith(
        "session",
        "motor-private-car",
        "v2",
        file,
      ),
    );
    expect(
      await screen.findByText("synthetic-reference.pdf"),
    ).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("was added");
  });
});

// Verify deletion is destructive only after an explicit confirmation.
describe("reference document deletion", () => {
  it("keeps the reference when the confirmation is refused", async () => {
    listReferencesMock.mockResolvedValue([STORED]);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderPanel();
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: "Remove" }),
    );

    expect(deleteReferenceMock).not.toHaveBeenCalled();
    expect(screen.getByText("synthetic-reference.pdf")).toBeTruthy();
    confirm.mockRestore();
  });

  it("removes the reference once it is confirmed", async () => {
    listReferencesMock.mockResolvedValue([STORED]);
    deleteReferenceMock.mockResolvedValue(undefined);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPanel();
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", { name: "Remove" }),
    );

    await waitFor(() =>
      expect(deleteReferenceMock).toHaveBeenCalledWith(
        "session",
        "motor-private-car",
        "reference-id",
      ),
    );
    expect(screen.queryByText("synthetic-reference.pdf")).toBeNull();
    expect(screen.getByRole("status").textContent).toContain("removed");
    confirm.mockRestore();
  });
});
