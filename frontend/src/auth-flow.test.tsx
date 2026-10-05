import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { safeReturnPath } from "@/auth/navigation";
import { anonymousSession, jsonResponse, noContentResponse, renderApp, requestFrom, unverifiedSession, verifiedSession } from "@/test/render";

function installFetch(handler: (request: Request) => Response | Promise<Response>) {
  const mock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => handler(requestFrom(input, init)));
  vi.stubGlobal("fetch", mock);
  return mock;
}

beforeEach(() => {
  document.cookie = "csrftoken=test-csrf; path=/";
});

afterEach(() => {
  document.cookie = "csrftoken=; Max-Age=0; path=/";
  vi.unstubAllGlobals();
});

describe("session routing", () => {
  it("does not flash protected content while session bootstrap is pending", () => {
    installFetch(() => new Promise<Response>(() => undefined));
    renderApp("/app");
    expect(screen.getByRole("status")).toHaveTextContent("Проверяем сессию");
    expect(screen.queryByRole("heading", { name: "Рабочее пространство" })).not.toBeInTheDocument();
  });

  it("redirects anonymous workspace access to login with a relative return path", async () => {
    installFetch(() => jsonResponse(anonymousSession));
    renderApp("/app");
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/login?returnTo=%2Fapp");
  });

  it("redirects authenticated visitors away from anonymous-only routes", async () => {
    installFetch(() => jsonResponse(verifiedSession));
    renderApp("/login");
    expect(await screen.findByRole("heading", { name: "Рабочее пространство" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/app");
  });
});

describe("authentication forms", () => {
  it("logs in with CSRF and rejects an external return target", async () => {
    let authenticated = false;
    let loginRequest: Request | undefined;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(authenticated ? unverifiedSession : anonymousSession);
      if (path === "/api/auth/login/") { loginRequest = request; authenticated = true; return jsonResponse({ user: unverifiedSession.user }); }
      throw new Error(`Unexpected request: ${path}`);
    });
    const user = userEvent.setup();
    renderApp("/login?returnTo=https%3A%2F%2Fevil.example%2Fsteal");
    await user.type(await screen.findByLabelText("Email"), "Applicant@Example.com");
    await user.type(screen.getByLabelText("Пароль"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByRole("heading", { name: "Рабочее пространство" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/app");
    expect(loginRequest?.headers.get("X-CSRFToken")).toBe("test-csrf");
    await expect(loginRequest?.clone().json()).resolves.toEqual({ email: "Applicant@Example.com", password: "correct-password" });
  });

  it("maps stable credential errors without account disclosure", async () => {
    installFetch((request) => new URL(request.url).pathname === "/api/auth/session/" ? jsonResponse(anonymousSession) : jsonResponse({ error: { code: "invalid_credentials", message: "Email or password is incorrect." } }, 400));
    const user = userEvent.setup();
    renderApp("/login");
    await user.type(await screen.findByLabelText("Email"), "nobody@example.com");
    await user.type(screen.getByLabelText("Пароль"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Неверный email или пароль");
  });

  it("maps rate limits with retry guidance", async () => {
    installFetch((request) => new URL(request.url).pathname === "/api/auth/session/" ? jsonResponse(anonymousSession) : jsonResponse({ error: { code: "rate_limited", message: "Too many requests." } }, 429, { "Retry-After": "60" }));
    const user = userEvent.setup();
    renderApp("/login");
    await user.type(await screen.findByLabelText("Email"), "applicant@example.com");
    await user.type(screen.getByLabelText("Пароль"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Доступно через 60 сек.");
  });

  it("captures and removes invitation token before registering", async () => {
    let authenticated = false;
    let registrationBody: unknown;
    installFetch(async (request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(authenticated ? unverifiedSession : anonymousSession);
      if (path === "/api/auth/register/") { registrationBody = await request.clone().json(); authenticated = true; return jsonResponse({ user: unverifiedSession.user }, 201); }
      throw new Error(`Unexpected request: ${path}`);
    });
    const user = userEvent.setup();
    renderApp("/register?invite=selector.secret&utm_source=email");
    expect(await screen.findByRole("heading", { name: "Регистрация" })).toBeVisible();
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/register?utm_source=email"));
    await user.type(screen.getByLabelText("Email из приглашения"), "applicant@example.com");
    await user.type(screen.getByLabelText("Пароль", { selector: "input" }), "strong-password");
    await user.type(screen.getByLabelText("Повторите пароль"), "strong-password");
    await user.click(screen.getByRole("button", { name: "Создать аккаунт" }));
    expect(await screen.findByRole("heading", { name: "Рабочее пространство" })).toBeVisible();
    expect(registrationBody).toEqual({ invitation_token: "selector.secret", email: "applicant@example.com", password: "strong-password" });
  });

  it("shows enumeration-safe password reset request success", async () => {
    installFetch((request) => new URL(request.url).pathname === "/api/auth/session/" ? jsonResponse(anonymousSession) : jsonResponse({ status: "accepted" }, 202));
    const user = userEvent.setup();
    renderApp("/forgot-password");
    await user.type(await screen.findByLabelText("Email"), "unknown@example.com");
    await user.click(screen.getByRole("button", { name: "Отправить ссылку" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Если аккаунт существует");
  });

  it("sanitizes reset tokens and submits the typed reset contract", async () => {
    let resetRequest: Request | undefined;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(anonymousSession);
      resetRequest = request; return noContentResponse();
    });
    const user = userEvent.setup();
    renderApp("/reset-password?uid=MQ&token=reset-secret");
    expect(await screen.findByRole("heading", { name: "Новый пароль" })).toBeVisible();
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/reset-password"));
    await user.type(screen.getByLabelText("Новый пароль", { selector: "input" }), "new-strong-password");
    await user.type(screen.getByLabelText("Повторите пароль"), "new-strong-password");
    await user.click(screen.getByRole("button", { name: "Сохранить пароль" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Пароль изменён");
    expect(resetRequest?.headers.get("X-CSRFToken")).toBe("test-csrf");
    await expect(resetRequest?.clone().json()).resolves.toEqual({ uid: "MQ", token: "reset-secret", new_password: "new-strong-password" });
  });

  it("sanitizes and confirms an email verification token", async () => {
    let confirmRequest: Request | undefined;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(anonymousSession);
      confirmRequest = request; return jsonResponse({ status: "verified" });
    });
    renderApp("/verify-email?token=verify.secret");
    expect(await screen.findByText("Email подтверждён.")).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/verify-email");
    expect(confirmRequest?.headers.get("X-CSRFToken")).toBe("test-csrf");
    await expect(confirmRequest?.clone().json()).resolves.toEqual({ token: "verify.secret" });
  });
});

describe("private workspace", () => {
  it("allows unverified access, resends verification, and logs out", async () => {
    const requests: Request[] = [];
    installFetch((request) => {
      requests.push(request);
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(unverifiedSession);
      if (path === "/api/auth/email-verification/request/") return jsonResponse({ status: "accepted" }, 202);
      if (path === "/api/auth/logout/") return noContentResponse();
      throw new Error(`Unexpected request: ${path}`);
    });
    const user = userEvent.setup();
    renderApp("/app");
    expect(await screen.findByText("Подтвердите email")).toBeVisible();
    expect(screen.getByText("applicant@example.com")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Отправить письмо повторно" }));
    expect(await screen.findByText("Письмо отправлено. Проверьте почту.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Выйти" }));
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeVisible();
    const unsafe = requests.filter((request) => request.method === "POST");
    expect(unsafe).toHaveLength(2);
    expect(unsafe.every((request) => request.headers.get("X-CSRFToken") === "test-csrf")).toBe(true);
  });

  it("does not show verification banner for verified users", async () => {
    installFetch(() => jsonResponse(verifiedSession));
    renderApp("/app");
    expect(await screen.findByRole("heading", { name: "Рабочее пространство" })).toBeVisible();
    expect(screen.queryByText("Подтвердите email")).not.toBeInTheDocument();
  });
});

describe("safe return paths", () => {
  it("accepts local relative paths and rejects external or scheme-relative paths", () => {
    expect(safeReturnPath("/app?tab=profile")).toBe("/app?tab=profile");
    expect(safeReturnPath("https://evil.example/x")).toBe("/app");
    expect(safeReturnPath("//evil.example/x")).toBe("/app");
    expect(safeReturnPath("/\\evil.example/x")).toBe("/app");
  });
});