import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { cacheProject } from "@/api/project-cache";
import { getApiErrorMessage } from "@/api/errors";
import { activateProject, deactivateProject, getProject, updateProject, type ProjectCreateInput } from "@/api/projects";
import { projectQueryKeys } from "@/api/project-query-keys";
import { useSession } from "@/auth/session";
import { ProjectForm } from "@/components/projects/project-form";

export function ProjectEditPage() {
  const { id = "" } = useParams();
  const session = useSession();
  const user = session.data?.user;
  const queryClient = useQueryClient();
  const project = useQuery({
    queryKey: projectQueryKeys.detail(user?.id ?? 0, id),
    queryFn: () => getProject(id),
    enabled: Boolean(user && id),
  });
  const lifecycle = useMutation({
    mutationFn: (action: "activate" | "deactivate") => action === "activate" ? activateProject(id) : deactivateProject(id),
  });

  if (!user) return null;
  const userId = user.id;
  const emailVerified = user.email_verified;

  async function save(input: ProjectCreateInput) {
    const updated = await updateProject(id, input);
    cacheProject(queryClient, userId, updated);
    return updated;
  }

  async function changeLifecycle(action: "activate" | "deactivate") {
    const updated = await lifecycle.mutateAsync(action);
    cacheProject(queryClient, userId, updated);
    return updated;
  }

  return <section className="rounded-lg border bg-card p-6 shadow-sm" aria-labelledby="project-title">
    <Link className="text-sm text-muted-foreground underline-offset-4 hover:underline" to="/app">← К списку проектов</Link>
    {project.isPending ? <p role="status" aria-live="polite" className="mt-6 text-muted-foreground">Загружаем проект…</p> : null}
    {project.isError ? <div role="alert" className="mt-6 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{getApiErrorMessage(project.error, "Не удалось загрузить проект.")}</div> : null}
    {project.data ? <>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 id="project-title" className="text-3xl font-bold">Редактирование проекта</h1>
        <span className="rounded-full bg-muted px-3 py-1 text-sm">{project.data.status === "active" ? "Активен" : "Черновик"}</span>
      </div>
      <ProjectForm project={project.data} emailVerified={emailVerified} isSaving={lifecycle.isPending} onSave={save} onLifecycle={changeLifecycle} />
    </> : null}
  </section>;
}
