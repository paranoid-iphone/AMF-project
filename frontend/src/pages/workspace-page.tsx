import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listProjects } from "@/api/projects";
import type { Project } from "@/api/projects";
import { projectQueryKeys } from "@/api/project-query-keys";
import { useSession } from "@/auth/session";

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatAmount(amount: string | null, currency: Project["currency"]) {
  if (amount === null) return "Сумма не указана";
  const [integerPart = "0", fractionPart = "00"] = amount.split(".");
  const groupedInteger = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(BigInt(integerPart));
  const decimalSeparator = new Intl.NumberFormat("ru-RU").formatToParts(1.1).find((part) => part.type === "decimal")?.value ?? ",";
  return `${groupedInteger}${decimalSeparator}${fractionPart} ${currency}`;
}

function compareUpdatedProjects(left: Project, right: Project) {
  return right.updated_at.localeCompare(left.updated_at) || right.created_at.localeCompare(left.created_at);
}

export function WorkspacePage() {
  const session = useSession();
  const user = session.data?.user;
  const projects = useQuery({
    queryKey: projectQueryKeys.list(user?.id ?? 0),
    queryFn: listProjects,
    enabled: Boolean(user),
  });

  if (!user) return null;
  const orderedProjects = projects.data ? [...projects.data].sort(compareUpdatedProjects) : [];

  return <section className="rounded-lg border bg-card p-6 shadow-sm" aria-labelledby="workspace-title">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Приватный кабинет</p>
        <h1 id="workspace-title" className="mt-2 text-3xl font-bold">Рабочее пространство</h1>
      </div>
      <Link className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" to="/app/projects/new">Создать проект</Link>
    </div>
    {projects.isPending ? <p role="status" aria-live="polite" className="mt-6 text-muted-foreground">Загружаем проекты…</p> : null}
    {projects.isError ? <div role="alert" className="mt-6 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">Не удалось загрузить проекты. Повторите попытку позже.</div> : null}
    {projects.isSuccess && orderedProjects.length === 0 ? <div className="mt-6 rounded-md border border-dashed p-6 text-center">
      <h2 className="font-semibold">У вас пока нет проектов</h2>
      <p className="mt-2 text-sm text-muted-foreground">Создайте черновик, чтобы начать работу над проектом.</p>
      <Link className="mt-4 inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" to="/app/projects/new">Создать проект</Link>
    </div> : null}
    {projects.isSuccess && orderedProjects.length > 0 ? <ul className="mt-6 grid gap-4" aria-label="Ваши проекты">
      {orderedProjects.map((project) => <li key={project.id}>
        <article className="rounded-md border bg-background p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h2 className="text-lg font-semibold"><Link className="underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" to={`/app/projects/${project.id}`}>{project.title}</Link></h2>
            <span className="rounded-full bg-muted px-3 py-1 text-sm">{project.status === "active" ? "Активен" : "Черновик"}</span>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">Инвестиции: {formatAmount(project.investment_amount, project.currency)}</p>
          <p className="mt-2 text-sm text-muted-foreground">Обновлён: <time dateTime={project.updated_at}>{dateFormatter.format(new Date(project.updated_at))}</time></p>
        </article>
      </li>)}
    </ul> : null}
  </section>;
}
