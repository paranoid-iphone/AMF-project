import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type AuthUser = components["schemas"]["User"];
export type SessionState = components["schemas"]["Session"];
export type ApiFieldErrors = components["schemas"]["ErrorDetail"]["fields"];

type ErrorCode = components["schemas"]["CodeEnum"];
type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];

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

const client = createClient<paths>({
  baseUrl: globalThis.location.origin,
  credentials: "same-origin",
  fetch: (request) => globalThis.fetch(request),
});

function getCookie(name: string) {
  const prefix = `${encodeURIComponent(name)}=`;
  const item = document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : "";
}

function csrfParameters() {
  return { header: { "X-CSRFToken": getCookie("csrftoken") } };
}

function throwApiError(error: ErrorEnvelope | undefined, response: Response): never {
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

export async function getSession(): Promise<SessionState> {
  const { data, error, response } = await client.GET("/api/auth/session/");
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}

export async function register(input: components["schemas"]["RegisterRequest"]): Promise<AuthUser> {
  const { data, error, response } = await client.POST("/api/auth/register/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data.user;
}

export async function login(input: components["schemas"]["LoginRequest"]): Promise<AuthUser> {
  const { data, error, response } = await client.POST("/api/auth/login/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data.user;
}

export async function logout(): Promise<void> {
  const { error, response } = await client.POST("/api/auth/logout/", {
    params: csrfParameters(),
  });
  if (!response.ok) throwApiError(error, response);
}

export async function requestEmailVerification(): Promise<void> {
  const { error, response } = await client.POST("/api/auth/email-verification/request/", {
    params: csrfParameters(),
  });
  if (!response.ok) throwApiError(error, response);
}

export async function confirmEmailVerification(token: string): Promise<void> {
  const { error, response } = await client.POST("/api/auth/email-verification/confirm/", {
    params: csrfParameters(),
    body: { token },
  });
  if (!response.ok) throwApiError(error, response);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const { error, response } = await client.POST("/api/auth/password-reset/request/", {
    params: csrfParameters(),
    body: { email },
  });
  if (!response.ok) throwApiError(error, response);
}

export async function confirmPasswordReset(input: components["schemas"]["PasswordResetConfirmRequest"]): Promise<void> {
  const { error, response } = await client.POST("/api/auth/password-reset/confirm/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok) throwApiError(error, response);
}