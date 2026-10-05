import type { QueryClient } from "@tanstack/react-query";

import type { Project } from "@/api/projects";
import { projectQueryKeys } from "@/api/project-query-keys";
import type { SessionState } from "@/api/auth";
import { sessionQueryKey } from "@/auth/session";

export function cacheProject(queryClient: QueryClient, userId: number, project: Project) {
  const session = queryClient.getQueryData<SessionState>(sessionQueryKey);
  if (!session?.authenticated || session.user?.id !== userId) return;
  queryClient.setQueryData(projectQueryKeys.detail(userId, project.id), project);
  queryClient.setQueryData<Project[]>(projectQueryKeys.list(userId), (current = []) => {
    const projects = current.filter((item) => item.id !== project.id);
    return [...projects, project].sort((left, right) => right.updated_at.localeCompare(left.updated_at) || right.created_at.localeCompare(left.created_at));
  });
}
