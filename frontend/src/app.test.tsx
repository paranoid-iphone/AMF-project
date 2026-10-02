import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "@/app";

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AMF status page", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("identifies the application and announces the loading state", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => undefined)));

    renderApp();

    expect(screen.getByRole("heading", { level: 1, name: "AMF application" })).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Checking API availability");
  });

  it("shows a success state when the typed health request succeeds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse({ status: "ok", database: "ok" }))),
    );

    renderApp();

    expect(await screen.findByText("All systems operational")).toBeVisible();
    expect(screen.getByText("API and database checks completed successfully.")).toBeVisible();
  });

  it("shows a failure state and lets the user retry", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ status: "unavailable", database: "unavailable" }, 503),
      )
      .mockResolvedValueOnce(jsonResponse({ status: "ok", database: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    renderApp();

    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
    await user.click(screen.getByRole("button", { name: "Retry health check" }));

    expect(await screen.findByText("All systems operational")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
