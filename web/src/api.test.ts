import { afterEach, describe, expect, it, vi } from "vitest";

import { removeDocument } from "./api";

// Restore the global request function after each typed-client check.
afterEach(() => {
  vi.unstubAllGlobals();
});

// Verify a successful deletion does not require a JSON response body.
describe("document API", () => {
  it("accepts a no-content document deletion", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(removeDocument("session", "case-id", "document-id"))
      .resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/cases/case-id/documents/document-id",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
