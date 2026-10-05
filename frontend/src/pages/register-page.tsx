import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { register as registerApplicant } from "@/api/auth";
import { applyApiFieldErrors, getApiErrorMessage } from "@/api/errors";
import { useRefreshSession } from "@/auth/session";
import { useSanitizedTokens } from "@/auth/tokens";
import { AuthShell, FormAlert } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/button";

const tokenNames = ["invite"] as const;
const schema = z.object({
  email: z.string().trim().min(1, "Введите email.").email("Введите корректный email."),
  password: z.string().min(8, "Пароль должен содержать не менее 8 символов."),
  passwordConfirmation: z.string().min(1, "Повторите пароль."),
}).refine((value) => value.password === value.passwordConfirmation, {
  path: ["passwordConfirmation"], message: "Пароли не совпадают.",
});
type Values = z.infer<typeof schema>;

export function RegisterPage() {
  const { invite } = useSanitizedTokens(tokenNames);
  const navigate = useNavigate();
  const refreshSession = useRefreshSession();
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "", passwordConfirmation: "" } });
  const mutation = useMutation({ mutationFn: registerApplicant });

  const submit = handleSubmit(async ({ email, password }) => {
    setFormError("");
    try {
      await mutation.mutateAsync({ invitation_token: invite, email, password });
      await refreshSession();
      void navigate("/app", { replace: true });
    } catch (error) {
      if (!applyApiFieldErrors(error, setError, ["email", "password"])) {
        setFormError(getApiErrorMessage(error, "Не удалось зарегистрироваться."));
      }
    }
  });

  if (!invite) {
    return <AuthShell title="Недействительная ссылка" description="Для регистрации требуется действующее приглашение."><FormAlert>Откройте ссылку из письма-приглашения или запросите новое приглашение у оператора.</FormAlert><Link className="mt-5 inline-block font-medium underline" to="/login">Перейти ко входу</Link></AuthShell>;
  }

  return (
    <AuthShell title="Регистрация" description="Создайте аккаунт по приглашению. Подтвердить email можно после входа." footer={<Link className="font-medium text-foreground underline" to="/login">Уже есть аккаунт? Войти</Link>}>
      <form className="space-y-5" onSubmit={(event) => void submit(event)} noValidate>
        {formError ? <FormAlert>{formError}</FormAlert> : null}
        <FormField label="Email из приглашения" type="email" autoComplete="email" registration={register("email")} error={errors.email} />
        <FormField label="Пароль" type="password" autoComplete="new-password" hint="Не менее 8 символов. Сервер дополнительно проверит надёжность пароля." registration={register("password")} error={errors.password} />
        <FormField label="Повторите пароль" type="password" autoComplete="new-password" registration={register("passwordConfirmation")} error={errors.passwordConfirmation} />
        <Button className="w-full" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Создаём аккаунт…" : "Создать аккаунт"}</Button>
      </form>
    </AuthShell>
  );
}