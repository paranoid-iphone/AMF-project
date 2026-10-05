import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/auth";
import { activateProject, createProject, deactivateProject, getProject, listProjects, updateProject } from "@/api/projects";
import type { components } from "@/api/schema";
import { jsonResponse, requestFrom } from "@/test/render";

const project: components["schemas"]["Project"] = {
  id: "7f7b2f5a-8e9b-4aef-9ab3-28c624798d4f",
  title: "Solar plant",
  description: "Regional solar facility",
  investment_amount: "250000000.00",
  currency: "KZT",
  status: "draft",
  created_at: "2026-10-05T10:00:00Z",
  updated_at: "2026-10-05T10:00:00Z",
  activated_at: null,
};

beforeEach(() => {
  document.cookie = "csrftoken=test-csrf; path=/";
});

afterEach(() => {
  document.cookie = "csrftoken=; Max-Age=0; path=/";
  vi.unstubAllGlobals();
});

describe("project HTTP transport", () => {
  it("uses the project endpoints, current CSRF token, and preserves request field presence", async () => {
    const requests: Request[] = [];
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const request = requestFrom(input, init);
      requests.push(request);
      const body = request.method === "POST" && new URL(request.url).pathname === "/api/projects/"
        ? project
        : new URL(request.url).pathname === "/api/projects/"
          ? { projects: [project] }
          : project;
      return Promise.resolve(jsonResponse(body, request.method === "POST" && new URL(request.url).pathname === "/api/projects/" ? 201 : 200));
    }));

    await expect(listProjects()).resolves.toEqual([project]);
    await expect(getProject(project.id)).resolves.toEqual(project);
    document.cookie = "csrftoken=create-csrf; path=/";
    await expect(createProject({ title: "New SPV" })).resolves.toEqual(project);
    document.cookie = "csrftoken=updated-csrf; path=/";
    await expect(updateProject(project.id, { description: "" })).resolves.toEqual(project);
    document.cookie = "csrftoken=activate-csrf; path=/";
    await expect(activateProject(project.id)).resolves.toEqual(project);
    document.cookie = "csrftoken=deactivate-csrf; path=/";
    await expect(deactivateProject(project.id)).resolves.toEqual(project);

    expect(requests.map(({ method, url }) => [method, new URL(url).pathname])).toEqual([
      ["GET", "/api/projects/"],
      ["GET", `/api/projects/${project.id}/`],
      ["POST", "/api/projects/"],
      ["PATCH", `/api/projects/${project.id}/`],
      ["POST", `/api/projects/${project.id}/activate/`],
      ["POST", `/api/projects/${project.id}/deactivate/`],
    ]);
    const mutations = requests.filter(({ method }) => method !== "GET");
    expect(mutations.map((request) => request.headers.get("X-CSRFToken"))).toEqual([
      "create-csrf",
      "updated-csrf",
      "activate-csrf",
      "deactivate-csrf",
    ]);
    await expect(requests[2]!.clone().json()).resolves.toEqual({ title: "New SPV" });
    await expect(requests[3]!.clone().json()).resolves.toEqual({ description: "" });
    expect(requests[4]!.body).toBeNull();
    expect(requests[5]!.body).toBeNull();
  });

  it("preserves stable field errors from the server", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({
      error: {
        code: "validation_error",
        message: "Request validation failed.",
        fields: { title: [{ code: "blank", message: "This field may not be blank." }] },
      },
    }, 400))));

    await expect(createProject({ title: "" })).rejects.toMatchObject({
      name: "ApiError",
      code: "validation_error",
      message: "Request validation failed.",
      fields: { title: [{ code: "blank", message: "This field may not be blank." }] },
    });
  });

  it("dispatches the global unauthorized event for a project 401", async () => {
    const unauthorized = vi.fn();
    globalThis.addEventListener("auth:unauthorized", unauthorized);
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({
      error: { code: "not_authenticated", message: "Authentication required." },
    }, 401))));

    await expect(listProjects()).rejects.toBeInstanceOf(ApiError);
    expect(unauthorized).toHaveBeenCalledTimes(1);
    globalThis.removeEventListener("auth:unauthorized", unauthorized);
  });

  it("preserves email verification errors from activation", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({
      error: { code: "email_verification_required", message: "Email verification is required." },
    }, 403))));

    await expect(activateProject(project.id)).rejects.toMatchObject({
      code: "email_verification_required",
      message: "Email verification is required.",
    });
  });

  it("preserves retry guidance from the response header", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({
      error: { code: "rate_limited", message: "Too many requests." },
    }, 429, { "Retry-After": "60" }))));

    await expect(createProject({ title: "New SPV" })).rejects.toMatchObject({
      code: "rate_limited",
      retryAfter: "60",
    });
  });

  it("uses the unexpected error fallback when the server has no stable error envelope", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("upstream failure", { status: 502 }))));

    await expect(listProjects()).rejects.toMatchObject({
      code: "unexpected_error",
      message: "The request could not be completed.",
    });
  });

  it("lets network failures keep their existing fetch rejection", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));

    await expect(listProjects()).rejects.toThrow("Failed to fetch");
  });
});
