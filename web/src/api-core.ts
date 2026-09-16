// Shared request plumbing for every typed API slice.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  retryable: boolean;
  requestId: string | undefined;

  // Preserve safe status information for inline UI error states.
  constructor(
    status: number,
    message: string,
    code = "http_error",
    retryable = false,
    requestId?: string,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.requestId = requestId;
  }
}

// Read the sanitized {error: {…}} envelope, tolerating other error bodies.
export function parseErrorBody(status: number, body: unknown): ApiError {
  const envelope = (body ?? {}) as {
    error?: {
      code?: string;
      message?: string;
      request_id?: string;
      retryable?: boolean;
    };
    detail?: unknown;
    message?: unknown;
  };
  const inner = envelope.error;
  const fallback = typeof envelope.detail === "string"
    ? envelope.detail
    : typeof envelope.message === "string"
      ? envelope.message
      : undefined;
  const message = typeof inner?.message === "string"
    ? inner.message
    : fallback ?? "The request could not be completed.";
  return new ApiError(
    status,
    message,
    inner?.code ?? "http_error",
    inner?.retryable ?? false,
    inner?.request_id,
  );
}

let unauthorizedHandler: (() => void) | null = null;

// Register the single recovery path used when a session stops being valid.
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export interface BlobResponse {
  blob: Blob;
  contentType: string;
  filename: string;
}

// Read an optional filename from a Content-Disposition header value.
function filenameFromDisposition(header: string | null): string {
  if (!header) return "";
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(header);
  return match ? match[1].trim() : "";
}

// Call one typed API endpoint and normalize safe error text.
export async function request<T>(
  path: string,
  token: string | undefined,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    // An expired token is recoverable: let the shell offer a fresh sign-in.
    if (response.status === 401 && token) unauthorizedHandler?.();
    const body = await response.json().catch(() => undefined);
    throw parseErrorBody(response.status, body);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// Fetch one binary endpoint and return its bytes plus safe media headers.
export async function requestBlob(
  path: string,
  token: string | undefined,
  init?: RequestInit,
): Promise<BlobResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    // An expired token is recoverable: let the shell offer a fresh sign-in.
    if (response.status === 401 && token) unauthorizedHandler?.();
    const body = await response.json().catch(() => undefined);
    throw parseErrorBody(response.status, body);
  }
  const blob = await response.blob();
  return {
    blob,
    contentType:
      response.headers.get("Content-Type") ?? "application/octet-stream",
    filename: filenameFromDisposition(
      response.headers.get("Content-Disposition"),
    ),
  };
}
