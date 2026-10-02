import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

const client = createClient<paths>({
  baseUrl: globalThis.location.origin,
  credentials: "same-origin",
  fetch: (request) => globalThis.fetch(request),
});

export type HealthResponse = components["schemas"]["Health"];

export async function getHealth(): Promise<HealthResponse> {
  const { data, response } = await client.GET("/api/health/");

  if (!response.ok || !data) {
    throw new Error("The AMF service is unavailable.");
  }

  if (data.status !== "ok" || data.database !== "ok") {
    throw new Error("The AMF service returned an unexpected status.");
  }

  return data;
}
