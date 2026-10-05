import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, renderApp, requestFrom, verifiedSession } from "@/test/render";
import { projectQueryKeys } from "@/api/project-query-keys";
import { sessionQueryKey } from "@/auth/session";

function installFetch(handler: (request: Request) => Response | Promise<Response>) {
  const mock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => handler(requestFrom(input, init)));
  vi.stubGlobal("fetch", mock);
  return mock;
}

const projectA = {
  id: "project-a",
  title: "Солнечная электростанция",
  description: "Региональная станция",
  investment_amount: "250000000.00",
  currency: "KZT",
  status: "draft",
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-02T10:00:00Z",
  activated_at: null,
} as const;

const projectB = {
  ...projectA,
  id: "project-b",
  title: "Ветряная электростанция",
  investment_amount: "1200.50",
  currency: "USD",
  status: "active",
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-03T10:00:00Z",
  activated_at: "2026-10-03T10:00:00Z",
} as const;

const activeProject = { ...projectA, status: "active", activated_at: "2026-10-02T10:00:00Z" } as const;

function apiRequest(request: Request, projectResponse: unknown) {
  const path = new URL(request.url).pathname;
  if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
  if (path === "/api/projects/") return jsonResponse(projectResponse);
  if (path === "/api/projects/project-a/") return jsonResponse(projectA);
  throw new Error(`Unexpected request: ${path}`);
}

beforeEach(() => {
  document.cookie = "csrftoken=test-csrf; path=/";
});

afterEach(() => {
  document.cookie = "csrftoken=; Max-Age=0; path=/";
  vi.unstubAllGlobals();
});

describe("private project workspace", () => {
  it("announces while the owner's projects are loading", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      return new Promise<Response>(() => undefined);
    });

    renderApp("/app");

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Загружаем проекты"));
  });

  it("shows a recoverable error when the project list cannot load", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      return jsonResponse({ error: { code: "unexpected_error", message: "Request failed." } }, 503);
    });

    renderApp("/app");

    expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить проекты.");
  });

  it("offers draft creation when the owner has no projects", async () => {
    installFetch((request) => apiRequest(request, { projects: [] }));
    const user = userEvent.setup();

    renderApp("/app");

    expect(await screen.findByText("У вас пока нет проектов")).toBeVisible();
    const createLink = screen.getAllByRole("link", { name: "Создать проект" })[0];
    if (!createLink) throw new Error("Create project link is missing");
    await user.click(createLink);
    expect(await screen.findByRole("heading", { name: "Новый проект" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/app/projects/new");
  });

  it("renders projects in last-updated order with Russian amount, status, and time", async () => {
    installFetch((request) => apiRequest(request, { projects: [{ ...projectA, investment_amount: "999999999999999999.99" }, projectB] }));

    renderApp("/app");

    const newer = await screen.findByRole("link", { name: "Ветряная электростанция" });
    const older = screen.getByRole("link", { name: "Солнечная электростанция" });
    const cards = screen.getAllByRole("article");
    const [newerCard, olderCard] = cards;
    if (!newerCard || !olderCard) throw new Error("Expected two project cards");
    expect(newerCard).toContainElement(newer);
    expect(olderCard).toContainElement(older);
    expect(within(newerCard).getByText(/1\s?200,50/)).toBeVisible();
    expect(within(newerCard).getByText("Активен")).toBeVisible();
    expect(within(olderCard).getByText("Черновик")).toBeVisible();
    expect(within(olderCard).getByText(/999\s?999\s?999\s?999\s?999\s?999,99 KZT/)).toBeVisible();
    expect(within(olderCard).getByText(/2\s?октября 2026/i)).toBeVisible();
    expect(screen.queryByRole("button", { name: /удалить|опубликовать|контакт/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /публичный|контакт/i })).not.toBeInTheDocument();
  });

  it("opens a private project from its card", async () => {
    installFetch((request) => apiRequest(request, { projects: [projectA] }));
    const user = userEvent.setup();

    renderApp("/app");

    await user.click(await screen.findByRole("link", { name: "Солнечная электростанция" }));
    expect(await screen.findByRole("heading", { name: "Редактирование проекта" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/app/projects/project-a");
  });
});

describe("project editor", () => {
  it("saves a new draft explicitly and redirects to its private editor", async () => {
    let createRequest: Request | undefined;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/" && request.method === "POST") {
        createRequest = request;
        return jsonResponse(projectA, 201);
      }
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(projectA);
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/new");

    await user.type(await screen.findByLabelText("Название проекта"), "Солнечная электростанция");
    expect(createRequest).toBeUndefined();
    await user.click(screen.getByRole("button", { name: "Сохранить черновик" }));

    expect(await screen.findByRole("heading", { name: "Редактирование проекта" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent("/app/projects/project-a");
    await expect(createRequest?.clone().json()).resolves.toEqual({ title: "Солнечная электростанция", description: "", investment_amount: null, currency: "KZT" });
    expect(createRequest?.headers.get("X-CSRFToken")).toBe("test-csrf");
  });

  it("loads and saves an existing project without a page reload", async () => {
    let patchRequest: Request | undefined;
    let savedTitle: string = projectA.title;
    installFetch(async (request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse({ ...projectA, title: savedTitle });
      if (path === "/api/projects/project-a/" && request.method === "PATCH") {
        patchRequest = request;
        const body = await request.clone().json() as { title: string };
        savedTitle = body.title;
        return jsonResponse({ ...projectA, title: body.title });
      }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    const title = await screen.findByLabelText("Название проекта");
    await user.clear(title);
    await user.type(title, "Новый заголовок");
    expect(patchRequest).toBeUndefined();
    await user.click(screen.getByRole("button", { name: "Сохранить изменения" }));

    await waitFor(() => expect(screen.getByLabelText("Название проекта")).toHaveValue("Новый заголовок"));
    expect(screen.getByTestId("location")).toHaveTextContent("/app/projects/project-a");
    expect(patchRequest?.headers.get("X-CSRFToken")).toBe("test-csrf");
  });

  it("activates a complete saved draft", async () => {
    let activated = false;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(activated ? activeProject : projectA);
      if (path === "/api/projects/project-a/activate/") { activated = true; return jsonResponse(activeProject); }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    await user.click(await screen.findByRole("button", { name: "Активировать проект" }));
    expect(await screen.findByText("Активен")).toBeVisible();
    expect(screen.getByRole("button", { name: "Вернуть в черновик" })).toBeEnabled();
  });

  it("returns an active project to draft and updates the saved status", async () => {
    let draft = false;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(draft ? projectA : activeProject);
      if (path === "/api/projects/project-a/deactivate/") { draft = true; return jsonResponse(projectA); }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    await user.click(await screen.findByRole("button", { name: "Вернуть в черновик" }));
    expect(await screen.findByText("Проект возвращён в черновик.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Активировать проект" })).toBeEnabled();
  });

  it("rejects an amount over the precision boundary without sending it", async () => {
    let createCalled = false;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/" && request.method === "POST") { createCalled = true; return jsonResponse(projectA, 201); }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/new");

    await user.type(await screen.findByLabelText("Название проекта"), "Проект с некорректной суммой");
    await user.type(screen.getByLabelText("Сумма инвестиций"), "1.234");
    await user.click(screen.getByRole("button", { name: "Сохранить черновик" }));

    expect(await screen.findByText("Укажите сумму не более чем с 20 цифрами и 2 знаками после запятой.")).toBeVisible();
    expect(createCalled).toBe(false);
  });

  it("requires saving edits before returning an active project to draft", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(activeProject);
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    const title = await screen.findByLabelText("Название проекта");
    await user.type(title, " обновление");
    expect(screen.getByRole("button", { name: "Вернуть в черновик" })).toBeDisabled();
    expect(screen.getByText("Сначала сохраните изменения, чтобы изменить статус проекта.")).toBeVisible();
  });

  it("blocks an active edit that would make its description incomplete", async () => {
    let patchCalled = false;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(activeProject);
      if (path === "/api/projects/project-a/" && request.method === "PATCH") { patchCalled = true; return jsonResponse(activeProject); }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    await user.clear(await screen.findByLabelText("Описание проекта"));
    await user.click(screen.getByRole("button", { name: "Сохранить изменения" }));

    expect(await screen.findByText("Заполните описание, чтобы активный проект оставался корректным.")).toBeVisible();
    expect(patchCalled).toBe(false);
  });

  it("translates server validation codes into Russian field guidance", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(projectA);
      if (path === "/api/projects/project-a/" && request.method === "PATCH") return jsonResponse({ error: { code: "validation_error", message: "Request validation failed.", fields: { title: [{ code: "max_length", message: "Ensure this field has no more than 200 characters." }] } } }, 400);
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    const title = await screen.findByLabelText("Название проекта");
    await user.clear(title);
    await user.type(title, "Обновлённый проект");
    await user.click(screen.getByRole("button", { name: "Сохранить изменения" }));

    expect(await screen.findByText("Превышена допустимая длина поля.")).toBeVisible();
  });

  it("keeps decimal precision for a maximum-size investment amount", async () => {
    let patchBody: unknown;
    const exactProject = { ...projectA, investment_amount: "999999999999999999.99" };
    installFetch(async (request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(exactProject);
      if (path === "/api/projects/project-a/" && request.method === "PATCH") {
        patchBody = await request.clone().json();
        return jsonResponse(exactProject);
      }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    const amount = await screen.findByLabelText("Сумма инвестиций");
    expect(amount).toHaveValue("999999999999999999.99");
    await user.type(screen.getByLabelText("Название проекта"), " — обновление");
    await user.click(screen.getByRole("button", { name: "Сохранить изменения" }));

    await waitFor(() => expect(patchBody).toEqual({ title: "Солнечная электростанция — обновление", description: "Региональная станция", investment_amount: "999999999999999999.99", currency: "KZT" }));
  });

  it("shows email verification guidance and disables activation for an unverified applicant", async () => {
    let activationRequested = false;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse({ authenticated: true, user: { ...verifiedSession.user, email_verified: false } });
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(projectA);
      if (path === "/api/projects/project-a/activate/") { activationRequested = true; return jsonResponse(projectA); }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });

    renderApp("/app/projects/project-a");

    expect(await screen.findByText("Подтверждение email потребуется, чтобы активировать проект.")).toBeVisible();
    expect(await screen.findByRole("button", { name: "Активировать проект" })).toBeDisabled();
    expect(screen.getByText("Подтвердите email, чтобы активировать проект.")).toBeVisible();
    expect(activationRequested).toBe(false);
  });

  it("asks for missing activation fields before calling the server", async () => {
    let activationRequested = false;
    const incomplete = { ...projectA, description: "", investment_amount: null };
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(incomplete);
      if (path === "/api/projects/project-a/activate/") { activationRequested = true; return jsonResponse(incomplete); }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    await user.click(await screen.findByRole("button", { name: "Активировать проект" }));
    expect(await screen.findByText("Заполните описание, чтобы активный проект оставался корректным.")).toBeVisible();
    expect(await screen.findByText("Укажите сумму инвестиций для активного проекта.")).toBeVisible();
    expect(activationRequested).toBe(false);
  });

  it("keeps entered values and shows no success when the session CSRF check fails", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/project-a/" && request.method === "GET") return jsonResponse(projectA);
      if (path === "/api/projects/project-a/" && request.method === "PATCH") return jsonResponse({ error: { code: "csrf_failed", message: "CSRF Failed." } }, 403);
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const user = userEvent.setup();

    renderApp("/app/projects/project-a");

    const title = await screen.findByLabelText("Название проекта");
    await user.clear(title);
    await user.type(title, "Несохранённое название");
    await user.click(screen.getByRole("button", { name: "Сохранить изменения" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Сессия безопасности устарела");
    expect(title).toHaveValue("Несохранённое название");
    expect(screen.queryByText("Изменения сохранены.")).not.toBeInTheDocument();
  });

  it("removes private account-scoped project cache when the real unauthorized bridge fires", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/") return jsonResponse({ projects: [] });
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const { queryClient } = renderApp("/app");

    expect(await screen.findByText("У вас пока нет проектов")).toBeVisible();
    queryClient.setQueryData(projectQueryKeys.list(verifiedSession.user.id), [projectA]);
    queryClient.setQueryData(projectQueryKeys.detail(verifiedSession.user.id, projectA.id), projectA);
    expect(queryClient.getQueryData(projectQueryKeys.list(verifiedSession.user.id))).toEqual([projectA]);

    let resolveLateSession: ((session: typeof verifiedSession) => void) | undefined;
    const lateSession = new Promise<typeof verifiedSession>((resolve) => { resolveLateSession = resolve; });
    const pendingSessionRefresh = queryClient.fetchQuery({ queryKey: sessionQueryKey, queryFn: () => lateSession, staleTime: 0 });
    void pendingSessionRefresh.catch(() => undefined);

    globalThis.dispatchEvent(new Event("auth:unauthorized"));
    resolveLateSession?.(verifiedSession);

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeVisible();
    await waitFor(() => {
      const projectData = queryClient.getQueriesData({ queryKey: projectQueryKeys.all }).map(([, data]) => data);
      expect(projectData.every((data) => data === undefined)).toBe(true);
    });
    expect(queryClient.getQueryData(sessionQueryKey)).toEqual({ authenticated: false, user: null });
  });

  it("cancels and removes private project queries when the owner logs out", async () => {
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/") return jsonResponse({ projects: [] });
      if (path === "/api/auth/logout/") return jsonResponse({ status: "ok" });
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const { queryClient } = renderApp("/app");
    const user = userEvent.setup();

    expect(await screen.findByText("У вас пока нет проектов")).toBeVisible();
    queryClient.setQueryData(projectQueryKeys.detail(verifiedSession.user.id, projectA.id), projectA);
    await user.click(screen.getByRole("button", { name: "Выйти" }));

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeVisible();
    await waitFor(() => {
      const projectData = queryClient.getQueriesData({ queryKey: projectQueryKeys.all }).map(([, data]) => data);
      expect(projectData.every((data) => data === undefined)).toBe(true);
    });
  });

  it("switches project reads to the new account-scoped cache after the session changes", async () => {
    let listRequests = 0;
    installFetch((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/session/") return jsonResponse(verifiedSession);
      if (path === "/api/projects/") {
        listRequests += 1;
        return jsonResponse({ projects: listRequests === 1 ? [projectA] : [projectB] });
      }
      throw new Error(`Unexpected request: ${request.method} ${path}`);
    });
    const { queryClient } = renderApp("/app");

    expect(await screen.findByRole("link", { name: "Солнечная электростанция" })).toBeVisible();
    queryClient.setQueryData(sessionQueryKey, { authenticated: true, user: { id: 2, email: "another@example.com", email_verified: true } });

    expect(await screen.findByRole("link", { name: "Ветряная электростанция" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Солнечная электростанция" })).not.toBeInTheDocument();
    expect(screen.getByText("another@example.com")).toBeVisible();
    expect(queryClient.getQueryData(projectQueryKeys.list(1))).toEqual([projectA]);
    expect(queryClient.getQueryData(projectQueryKeys.list(2))).toEqual([projectB]);
  });
});
