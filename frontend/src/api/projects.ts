import { apiClient, csrfParameters, throwApiError } from "@/api/client";
import type { components } from "@/api/schema";

export type Project = components["schemas"]["Project"];
export type ProjectCreateInput = components["schemas"]["ProjectWriteRequest"];
export type ProjectPatch = components["schemas"]["PatchedProjectWriteRequest"];

export async function listProjects(): Promise<Project[]> {
  const { data, error, response } = await apiClient.GET("/api/projects/");
  if (!response.ok || !data) throwApiError(error, response);
  return data.projects;
}

export async function getProject(id: string): Promise<Project> {
  const { data, error, response } = await apiClient.GET("/api/projects/{id}/", {
    params: { path: { id } },
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}

export async function createProject(input: ProjectCreateInput): Promise<Project> {
  const { data, error, response } = await apiClient.POST("/api/projects/", {
    params: csrfParameters(),
    body: input,
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}

export async function updateProject(id: string, patch: ProjectPatch): Promise<Project> {
  const { data, error, response } = await apiClient.PATCH("/api/projects/{id}/", {
    params: { ...csrfParameters(), path: { id } },
    body: patch,
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}

export async function activateProject(id: string): Promise<Project> {
  const { data, error, response } = await apiClient.POST("/api/projects/{id}/activate/", {
    params: { ...csrfParameters(), path: { id } },
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}

export async function deactivateProject(id: string): Promise<Project> {
  const { data, error, response } = await apiClient.POST("/api/projects/{id}/deactivate/", {
    params: { ...csrfParameters(), path: { id } },
  });
  if (!response.ok || !data) throwApiError(error, response);
  return data;
}
