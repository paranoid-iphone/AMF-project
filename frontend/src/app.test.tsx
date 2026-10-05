import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jsonResponse, renderApp } from "@/test/render";

describe("AMF status page", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("identifies the application and announces the loading state", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => undefined)));
    renderApp("/status");
    expect(screen.getByRole("heading", { level: 1, name: "AMF application" })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Checking API availability");
  });

  it("shows success when health succeeds", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({ status: "ok", database: "ok" }))));
    renderApp("/status");
    expect(await screen.findByText("All systems operational")).toBeVisible();
  });

  it("shows failure and retries", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ status: "unavailable", database: "unavailable" }, 503)).mockResolvedValueOnce(jsonResponse({ status: "ok", database: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderApp("/status");
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    await user.click(screen.getByRole("button", { name: "Retry health check" }));
    expect(await screen.findByText("All systems operational")).toBeVisible();
  });
});