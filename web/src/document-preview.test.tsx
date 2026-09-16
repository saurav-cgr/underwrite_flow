// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => {
  class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  }
  return {
    ApiError,
    fetchReviewDocument: vi.fn(),
  };
});

import { ApiError, fetchReviewDocument } from "./api";
import { DocumentPreview } from "./document-preview";
import "./test-setup";

const PDF = new Blob(["%PDF-1.4"], { type: "application/pdf" });
const IMAGE = new Blob(["png"], { type: "image/png" });

// Provide the object-URL helpers jsdom lacks and track every revoke.
function stubBlobUrls() {
  let index = 0;
  const createUrl = vi.fn(() => `blob:mock-${++index}`);
  const revokeUrl = vi.fn();
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: createUrl,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: revokeUrl,
  });
  return { revokeUrl };
}

function renderPreview(
  overrides: Partial<Parameters<typeof DocumentPreview>[0]> = {},
) {
  const props = {
    caseId: "case-id",
    contentType: "application/pdf",
    documentId: "doc-1",
    onClose: vi.fn(),
    page: 2,
    title: "Synthetic vehicle record",
    token: "session",
    ...overrides,
  };
  return render(<DocumentPreview {...props} />);
}

describe("document preview", () => {
  let revokeUrl: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    revokeUrl = stubBlobUrls().revokeUrl;
    vi.mocked(fetchReviewDocument).mockResolvedValue({
      blob: PDF,
      contentType: "application/pdf",
      filename: "synthetic.pdf",
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads a PDF into a sandboxed, titled frame with its page", async () => {
    renderPreview();

    expect(screen.getByText("Loading document…")).toBeTruthy();

    const frame = await screen.findByTitle("Synthetic vehicle record");
    expect(frame.tagName).toBe("IFRAME");
    expect(frame.getAttribute("sandbox")).not.toBeNull();
    expect((frame as HTMLIFrameElement).src).toBe("blob:mock-1#page=2");
  });

  it("renders an image with meaningful alternative text", async () => {
    vi.mocked(fetchReviewDocument).mockResolvedValue({
      blob: IMAGE,
      contentType: "image/png",
      filename: "synthetic.png",
    });
    renderPreview({ contentType: "image/png", page: 1 });

    const image = await screen.findByAltText(
      "Synthetic vehicle record · Page 1",
    );
    expect(image.tagName).toBe("IMG");
  });

  it("surfaces an unavailable document and retries it", async () => {
    vi.mocked(fetchReviewDocument).mockRejectedValueOnce(
      new ApiError(404, "Document not found"),
    );
    renderPreview();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Document not found");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByTitle("Synthetic vehicle record")).toBeTruthy();
  });

  it("opens the document in a new tab", async () => {
    const open = vi.fn();
    Object.defineProperty(window, "open", {
      configurable: true,
      value: open,
    });
    renderPreview();
    await screen.findByTitle("Synthetic vehicle record");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /open in new tab/i }));

    expect(open).toHaveBeenCalledWith(
      "blob:mock-1#page=2",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("closes and revokes the object URL on unmount", async () => {
    const { unmount } = renderPreview();
    await screen.findByTitle("Synthetic vehicle record");

    unmount();

    expect(revokeUrl).toHaveBeenCalledWith("blob:mock-1");
  });

  it("revokes the previous object URL when a new document loads", async () => {
    const { rerender } = renderPreview();
    await screen.findByTitle("Synthetic vehicle record");

    vi.mocked(fetchReviewDocument).mockResolvedValue({
      blob: PDF,
      contentType: "application/pdf",
      filename: "other.pdf",
    });
    rerender(
      <DocumentPreview
        caseId="case-id"
        contentType="application/pdf"
        documentId="doc-2"
        onClose={vi.fn()}
        page={null}
        title="Other record"
        token="session"
      />,
    );

    await screen.findByTitle("Other record");
    expect(revokeUrl).toHaveBeenCalledWith("blob:mock-1");
  });
});
