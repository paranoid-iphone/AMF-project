import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { requestPasswordReset } from "@/api/auth";
import { applyApiFieldErrors, getApiErrorMessage } from "@/api/errors";
import { AuthShell, FormAlert, SuccessMessage } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/button";

const schema = z.object({ email: z.string().trim().min(1, "Введите email.").email("Введите корректный email.") });
type Values = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: "" } });
  const mutation = useMutation({ mutationFn: requestPasswordReset });
  const submit = handleSubmit(async ({ email }) => {
    setFormError("");
    try {
      await mutation.mutateAsync(email);
      setSubmitted(true);
    } catch (error) {
      if (!applyApiFieldErrors(error, setError, ["email"])) setFormError(getApiErrorMessage(error, "Не удалось отправить запрос."));
    }
  });

  return <AuthShell title="Восстановление пароля" description="Укажите email аккаунта. Ответ одинаков независимо от наличия аккаунта." footer={<Link className="font-medium text-foreground underline" to="/login">Вернуться ко входу</Link>}>
    {submitted ? <SuccessMessage>Если аккаунт существует, письмо со ссылкой уже отправлено. Проверьте почту.</SuccessMessage> : <form className="space-y-5" onSubmit={(event) => void submit(event)} noValidate>
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <FormField label="Email" type="email" autoComplete="email" registration={register("email")} error={errors.email} />
      <Button className="w-full" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Отправляем…" : "Отправить ссылку"}</Button>
    </form>}
  </AuthShell>;
}