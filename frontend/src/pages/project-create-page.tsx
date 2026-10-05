import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { cacheProject } from "@/api/project-cache";
import { createProject, type ProjectCreateInput } from "@/api/projects";
import { useSession } from "@/auth/session";
import { ProjectForm } from "@/components/projects/project-form";

export function ProjectCreatePage() {
  const session = useSession();
  const user = session.data?.user;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const create = useMutation({ mutationFn: createProject });

  if (!user) return null;
  const userId = user.id;
  const emailVerified = user.email_verified;

  async function save(input: ProjectCreateInput) {
    const project = await create.mutateAsync(input);
    cacheProject(queryClient, userId, project);
    void navigate(`/app/projects/${project.id}`, { replace: true });
    return project;
  }

  return <section className="rounded-lg border bg-card p-6 shadow-sm" aria-labelledby="project-title">
    <Link className="text-sm text-muted-foreground underline-offset-4 hover:underline" to="/app">← К списку проектов</Link>
    <h1 id="project-title" className="mt-3 text-3xl font-bold">Новый проект</h1>
    <p className="mt-2 text-sm text-muted-foreground">Создайте приватный черновик. Его увидите только вы.</p>
    <ProjectForm project={null} emailVerified={emailVerified} isSaving={create.isPending} onSave={save} />
  </section>;
}
