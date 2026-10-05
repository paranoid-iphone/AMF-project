import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

type ErrorCode = components["schemas"]["CodeEnum"];
type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];

export type ApiFieldErrors = components["schemas"]["ErrorDetail"]["fields"];

export class ApiError extends Error {
  constructor(
    public readonly code: ErrorCode | "unexpected_error",
    message: string,
    public readonly fields?: ApiFieldErrors,
    public readonly retryAfter?: string | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const apiClient = createClient<paths>({
  baseUrl: globalThis.location.origin,
  credentials: "same-origin",
  fetch: (request) => globalThis.fetch(request),
});

function getCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`;
  const item = document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : "";
}

export function csrfParameters() {
  return { header: { "X-CSRFToken": getCookie("csrftoken") } };
}

export function throwApiError(error: ErrorEnvelope | undefined, response: Response): never {
  if (response.status === 401) globalThis.dispatchEvent(new Event("auth:unauthorized"));
  if (error?.error) {
    throw new ApiError(
      error.error.code,
      error.error.message,
      error.error.fields,
      response.headers.get("Retry-After"),
    );
  }
  throw new ApiError("unexpected_error", "The request could not be completed.");
}
