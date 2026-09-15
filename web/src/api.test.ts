import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createSession,
  readCase,
  removeDocument,
  setUnauthorizedHandler,
} from "./api";

// Restore the global request function after each typed-client check.
afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
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

// Verify the sanitized {error: {…}} envelope reaches the caller intact.
describe("error envelope", () => {
  function stubResponse(status: number, body: unknown) {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(body), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  }

  it("reads the message, code, and retryable flag from the envelope",
    async () => {
    stubResponse(409, {
      error: {
        code: "conflict",
        message: "Case has no confirmed final route",
        request_id: "synthetic-request",
        retryable: true,
      },
    });

    const error = await readCase("session", "case-id").catch(
      (thrown: unknown) => thrown,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).message).toBe(
      "Case has no confirmed final route",
    );
    expect((error as ApiError).code).toBe("conflict");
    expect((error as ApiError).retryable).toBe(true);
    expect((error as ApiError).requestId).toBe("synthetic-request");
  });

  it("never invents a message when the envelope is absent", async () => {
    stubResponse(500, null);

    const error = await readCase("session", "case-id").catch(
      (thrown: unknown) => thrown,
    );

    expect((error as ApiError).message).toBe(
      "The request could not be completed.",
    );
    expect((error as ApiError).retryable).toBe(false);
  });

  it("notifies the shell once when a session is no longer valid", async () => {
    stubResponse(401, {
      error: { code: "unauthorized", message: "Session expired" },
    });
    const handler = vi.fn();
    setUnauthorizedHandler(handler);

    await readCase("stale-session", "case-id").catch(() => undefined);

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does not sign the user out on a rejected sign-in attempt", async () => {
    stubResponse(401, {
      error: { code: "unauthorized", message: "Invalid credentials" },
    });
    const handler = vi.fn();
    setUnauthorizedHandler(handler);

    await createSession("synthetic@test", "wrong").catch(() => undefined);

    expect(handler).not.toHaveBeenCalled();
  });
});
