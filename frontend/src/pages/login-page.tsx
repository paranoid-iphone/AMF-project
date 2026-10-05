import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { login } from "@/api/auth";
import { applyApiFieldErrors, getApiErrorMessage } from "@/api/errors";
import { safeReturnPath } from "@/auth/navigation";
import { useRefreshSession } from "@/auth/session";
import { AuthShell, FormAlert } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/button";

const schema = z.object({
  email: z.string().trim().min(1, "Введите email.").email("Введите корректный email."),
  password: z.string().min(1, "Введите пароль."),
});
type Values = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const refreshSession = useRefreshSession();
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });
  const mutation = useMutation({ mutationFn: login });

  const submit = handleSubmit(async (values) => {
    setFormError("");
    try {
      await mutation.mutateAsync(values);
      await refreshSession();
      void navigate(safeReturnPath(search.get("returnTo")), { replace: true });
    } catch (error) {
      if (!applyApiFieldErrors(error, setError, ["email", "password"])) {
        setFormError(getApiErrorMessage(error, "Не удалось войти. Повторите позже."));
      }
    }
  });

  return (
    <AuthShell title="Вход" description="Войдите в приватный кабинет заявителя." footer={<><Link className="font-medium text-foreground underline-offset-4 hover:underline" to="/forgot-password">Забыли пароль?</Link><p className="mt-2">Регистрация доступна только по приглашению.</p></>}>
      <form className="space-y-5" onSubmit={(event) => void submit(event)} noValidate>
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <FormField label="Email" type="email" autoComplete="email" registration={register("email")} error={errors.email} />
        <FormField label="Пароль" type="password" autoComplete="current-password" registration={register("password")} error={errors.password} />
        <Button className="w-full" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Входим…" : "Войти"}</Button>
      </form>
    </AuthShell>
  );
}