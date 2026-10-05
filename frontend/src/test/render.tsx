/* eslint-disable react-refresh/only-export-components */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";

import { App } from "@/app";

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location" hidden>{`${location.pathname}${location.search}`}</div>;
}

export function renderApp(initialEntry = "/") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<MemoryRouter initialEntries={[initialEntry]}><QueryClientProvider client={queryClient}><App /><LocationProbe /></QueryClientProvider></MemoryRouter>);
}

export function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

export function noContentResponse() {
  return new Response(null, { status: 204 });
}

export function requestFrom(input: RequestInfo | URL, init?: RequestInit) {
  return input instanceof Request ? input : new Request(input, init);
}

export const anonymousSession = { authenticated: false, user: null };
export const unverifiedSession = { authenticated: true, user: { id: 1, email: "applicant@example.com", email_verified: false } };
export const verifiedSession = { authenticated: true, user: { id: 1, email: "applicant@example.com", email_verified: true } };