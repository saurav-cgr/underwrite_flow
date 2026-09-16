import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createSession,
  deleteReference,
  listReferences,
  readCase,
  readCaseConfiguration,
  removeDocument,
  resubmitCase,
  setUnauthorizedHandler,
  submitCase,
  uploadReference,
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

// Stub one JSON response and return the fetch mock for assertions.
function stubJson(status: number, value: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(value), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// Verify the applicant lifecycle calls the owned case routes.
describe("case submission API", () => {
  const submission = {
    id: "case-id",
    status: "underwriter_review",
    recommendation: { route: "expedited", factors: [] },
  };

  it("submits an owned case for processing", async () => {
    const fetchMock = stubJson(200, submission);

    const result = await submitCase("session", "case-id");

    expect(result.status).toBe("underwriter_review");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/cases/case-id/submit",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("resubmits a case returned for information", async () => {
    const fetchMock = stubJson(200, submission);

    await resubmitCase("session", "case-id");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/cases/case-id/resubmit",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

// Verify the pinned configuration and reference documents use their routes.
describe("configuration and reference API", () => {
  it("reads the pinned configuration of one case", async () => {
    const fetchMock = stubJson(200, {
      case_id: "case-id",
      product_code: "motor-private-car",
      product_version: "v1",
      rulebook_version: "v1",
      fields: [],
      documents: [],
    });

    const configuration = await readCaseConfiguration(
      "session",
      "case-id",
    );

    expect(configuration.product_version).toBe("v1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/cases/case-id/configuration",
      expect.anything(),
    );
  });

  it("uploads a reference document as multipart form data", async () => {
    const fetchMock = stubJson(200, {
      id: "reference-id",
      version: "v1",
      filename: "synthetic.pdf",
      content_type: "application/pdf",
      byte_size: 32,
      content_hash: "synthetic",
      page_count: 1,
    });
    const file = new File(["synthetic"], "synthetic.pdf", {
      type: "application/pdf",
    });

    await uploadReference("session", "motor-private-car", "v1", file);

    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe(
      "/api/v1/products/motor-private-car/references",
    );
    expect(init.method).toBe("POST");
    const form = init.body as FormData;
    expect(form.get("version")).toBe("v1");
    expect(form.get("reference")).toBe(file);
  });

  it("lists reference documents for one product version", async () => {
    const fetchMock = stubJson(200, []);

    await listReferences("session", "motor-private-car", "v1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/products/motor-private-car/references?version=v1",
      expect.anything(),
    );
  });

  it("deletes one reference document", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 204 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      deleteReference("session", "motor-private-car", "reference-id"),
    ).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/products/motor-private-car/references/reference-id",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
