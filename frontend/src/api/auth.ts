import { apiClient, csrfParameters, throwApiError } from "@/api/client";
import type { components } from "./schema";

export { ApiError } from "@/api/client";
export type { ApiFieldErrors } from "@/api/client";

export type AuthUser = components["schemas"]["User"];
export type SessionState = components["schemas"]["Session"];
export async function getSession(): Promise<SessionState> {
  const { data, error, response } = await apiClient.GET("/api/auth/session/");
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}

export async function register(input: components["schemas"]["RegisterRequest"]): Promise<AuthUser> {
  const { data, error, response } = await apiClient.POST("/api/auth/register/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data.user;
}

export async function login(input: components["schemas"]["LoginRequest"]): Promise<AuthUser> {
  const { data, error, response } = await apiClient.POST("/api/auth/login/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data.user;
}

export async function logout(): Promise<void> {
  const { error, response } = await apiClient.POST("/api/auth/logout/", {
    params: csrfParameters(),
  });
  if (!response.ok) throwApiError(error, response);
}

export async function requestEmailVerification(): Promise<void> {
  const { error, response } = await apiClient.POST("/api/auth/email-verification/request/", {
    params: csrfParameters(),
  });
  if (!response.ok) throwApiError(error, response);
}

export async function confirmEmailVerification(token: string): Promise<void> {
  const { error, response } = await apiClient.POST("/api/auth/email-verification/confirm/", {
    params: csrfParameters(),
    body: { token },
  });
  if (!response.ok) throwApiError(error, response);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const { error, response } = await apiClient.POST("/api/auth/password-reset/request/", {
    params: csrfParameters(),
    body: { email },
  });
  if (!response.ok) throwApiError(error, response);
}

export async function confirmPasswordReset(input: components["schemas"]["PasswordResetConfirmRequest"]): Promise<void> {
  const { error, response } = await apiClient.POST("/api/auth/password-reset/confirm/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok) throwApiError(error, response);
}
