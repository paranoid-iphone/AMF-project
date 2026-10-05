import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { getApiErrorMessage } from "@/api/errors";
import type { Project, ProjectCreateInput } from "@/api/projects";
import { Button } from "@/components/button";

type ProjectFormValues = {
  title: string;
  description: string;
  investment_amount: string;
  currency: Project["currency"];
};

type LifecycleAction = "activate" | "deactivate";

interface ProjectFormProps {
  project: Project | null;
  emailVerified: boolean;
  isSaving: boolean;
  onSave: (input: ProjectCreateInput) => Promise<Project>;
  onLifecycle?: (action: LifecycleAction) => Promise<Project>;
}

const baseSchema = z.object({
  title: z.string(),
  description: z.string(),
  investment_amount: z.string(),
  currency: z.enum(["KZT", "USD", "EUR"]),
});

function makeSchema(active: boolean) {
  return baseSchema.superRefine((values, context) => {
    const title = values.title.trim();
    if (!title) context.addIssue({ code: "custom", path: ["title"], message: "Введите название проекта." });
    if (title.length > 200) context.addIssue({ code: "custom", path: ["title"], message: "Название не должно быть длиннее 200 символов." });
    if (values.description.length > 5000) context.addIssue({ code: "custom", path: ["description"], message: "Описание не должно быть длиннее 5000 символов." });

    const amount = values.investment_amount.trim();
    if (amount && !/^\d{1,18}(?:\.\d{1,2})?$/.test(amount)) {
      context.addIssue({ code: "custom", path: ["investment_amount"], message: "Укажите сумму не более чем с 20 цифрами и 2 знаками после запятой." });
    } else if (amount && !/[1-9]/.test(amount)) {
      context.addIssue({ code: "custom", path: ["investment_amount"], message: "Сумма инвестиций должна быть больше нуля." });
    }

    if (active && !values.description.trim()) {
      context.addIssue({ code: "custom", path: ["description"], message: "Заполните описание, чтобы активный проект оставался корректным." });
    }
    if (active && !amount) {
      context.addIssue({ code: "custom", path: ["investment_amount"], message: "Укажите сумму инвестиций для активного проекта." });
    }
  });
}

function valuesFromProject(project: Project | null): ProjectFormValues {
  return {
    title: project?.title ?? "",
    description: project?.description ?? "",
    investment_amount: project?.investment_amount ?? "",
    currency: project?.currency ?? "KZT",
  };
}

const projectFieldMessages: Record<string, string> = {
  blank: "Заполните это поле.",
  max_length: "Превышена допустимая длина поля.",
  min_value: "Сумма инвестиций должна быть больше нуля.",
  max_decimal_places: "Сумма может содержать не более двух знаков после запятой.",
  max_digits: "Сумма превышает допустимое количество цифр.",
  invalid_choice: "Выберите поддерживаемую валюту.",
  required_for_activation: "Заполните это поле для активации проекта.",
};

function getProjectFieldMessage(code: string) {
  return projectFieldMessages[code] ?? "Проверьте введённое значение.";
}

export function ProjectForm({ project, emailVerified, isSaving, onSave, onLifecycle }: ProjectFormProps) {
  const [requestError, setRequestError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const active = project?.status === "active";
  const schema = useMemo(() => makeSchema(active), [active]);
  const form = useForm<ProjectFormValues>({
    resolver: zodResolver(schema) as Resolver<ProjectFormValues>,
    defaultValues: valuesFromProject(project),
  });
  const { register, handleSubmit, reset, setError, getValues, formState: { errors, isDirty, isSubmitting } } = form;
  const submitForm = handleSubmit(submit);
  const lifecyclePending = isSaving || isSubmitting;

  useEffect(() => {
    reset(valuesFromProject(project));
  }, [project, reset]);

  function applyFieldErrors(error: unknown) {
    if (!(error instanceof ApiError) || !error.fields) return false;
    let applied = false;
    for (const field of ["title", "description", "investment_amount", "currency"] as const) {
      const item = error.fields[field]?.[0];
      if (item) {
        setError(field, { type: "server", message: getProjectFieldMessage(item.code) });
        applied = true;
      }
    }
    return applied;
  }

  async function submit(values: ProjectFormValues) {
    setRequestError("");
    setSuccessMessage("");
    const input: ProjectCreateInput = {
      title: values.title.trim(),
      description: values.description,
      investment_amount: values.investment_amount.trim() || null,
      currency: values.currency,
    };
    try {
      const saved = await onSave(input);
      reset(valuesFromProject(saved));
      setSuccessMessage(project ? "Изменения сохранены." : "Черновик сохранён.");
    } catch (error) {
      if (!applyFieldErrors(error)) setRequestError(getApiErrorMessage(error, "Не удалось сохранить проект."));
    }
  }

  async function transition(action: LifecycleAction) {
    setRequestError("");
    setSuccessMessage("");
    if (action === "activate") {
      const validation = makeSchema(true).safeParse(getValues());
      if (!validation.success) {
        for (const issue of validation.error.issues) {
          const field = issue.path[0];
          if (field === "title" || field === "description" || field === "investment_amount" || field === "currency") {
            setError(field, { type: "activation", message: issue.message });
          }
        }
        return;
      }
    }
    if (!onLifecycle) return;
    try {
      const changed = await onLifecycle(action);
      reset(valuesFromProject(changed));
      setSuccessMessage(action === "activate" ? "Проект активирован." : "Проект возвращён в черновик.");
    } catch (error) {
      if (!applyFieldErrors(error)) setRequestError(getApiErrorMessage(error, "Не удалось изменить статус проекта."));
    }
  }

  const amountHint = "Можно оставить пустым в черновике. Максимум 20 цифр, не более 2 знаков после запятой.";

  return <form onSubmit={(event) => { void submitForm(event); }} noValidate className="mt-6 space-y-5">
    <div className="space-y-2">
      <label htmlFor="title" className="text-sm font-medium">Название проекта</label>
      <input id="title" maxLength={200} aria-invalid={Boolean(errors.title)} aria-describedby={errors.title ? "title-error" : undefined} className="min-h-11 w-full rounded-md border bg-background px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" {...register("title")} />
      {errors.title ? <p id="title-error" className="text-sm text-destructive">{errors.title.message}</p> : null}
    </div>
    <div className="space-y-2">
      <label htmlFor="description" className="text-sm font-medium">Описание проекта</label>
      <textarea id="description" rows={5} maxLength={5000} aria-invalid={Boolean(errors.description)} aria-describedby={errors.description ? "description-error" : undefined} className="w-full rounded-md border bg-background px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" {...register("description")} />
      {errors.description ? <p id="description-error" className="text-sm text-destructive">{errors.description.message}</p> : null}
    </div>
    <div className="space-y-2">
      <label htmlFor="investment_amount" className="text-sm font-medium">Сумма инвестиций</label>
      <input id="investment_amount" type="text" inputMode="decimal" autoComplete="off" aria-invalid={Boolean(errors.investment_amount)} aria-describedby={errors.investment_amount ? "investment_amount-error investment_amount-hint" : "investment_amount-hint"} className="min-h-11 w-full rounded-md border bg-background px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" {...register("investment_amount")} />
      <p id="investment_amount-hint" className="text-sm text-muted-foreground">{amountHint}</p>
      {errors.investment_amount ? <p id="investment_amount-error" className="text-sm text-destructive">{errors.investment_amount.message}</p> : null}
    </div>
    <div className="space-y-2">
      <label htmlFor="currency" className="text-sm font-medium">Валюта</label>
      <select id="currency" className="min-h-11 w-full rounded-md border bg-background px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" {...register("currency")}>
        <option value="KZT">KZT — тенге</option>
        <option value="USD">USD — доллар США</option>
        <option value="EUR">EUR — евро</option>
      </select>
    </div>
    {requestError ? <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{requestError}</div> : null}
    {successMessage ? <p role="status" className="rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900">{successMessage}</p> : null}
    <div className="flex flex-wrap gap-3">
      <Button type="submit" disabled={isSaving || isSubmitting}>{isSaving || isSubmitting ? "Сохраняем…" : project ? "Сохранить изменения" : "Сохранить черновик"}</Button>
      {project?.status === "draft" ? <Button type="button" disabled={lifecyclePending || isDirty || !emailVerified} onClick={() => void transition("activate")}>Активировать проект</Button> : null}
      {project?.status === "active" ? <Button type="button" disabled={lifecyclePending || isDirty} onClick={() => void transition("deactivate")}>Вернуть в черновик</Button> : null}
    </div>
    {isDirty && project ? <p className="text-sm text-muted-foreground">Сначала сохраните изменения, чтобы изменить статус проекта.</p> : null}
    {project?.status === "draft" && !emailVerified ? <p className="text-sm text-muted-foreground">Подтвердите email, чтобы активировать проект.</p> : null}
  </form>;
}
