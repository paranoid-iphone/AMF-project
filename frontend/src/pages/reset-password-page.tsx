import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { confirmPasswordReset } from "@/api/auth";
import { applyApiFieldErrors, getApiErrorMessage } from "@/api/errors";
import { useSanitizedTokens } from "@/auth/tokens";
import { AuthShell, FormAlert, SuccessMessage } from "@/components/auth/auth-shell";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/button";

const tokenNames = ["uid", "token"] as const;
const schema = z.object({
  new_password: z.string().min(8, "Пароль должен содержать не менее 8 символов."),
  confirmation: z.string().min(1, "Повторите пароль."),
}).refine((value) => value.new_password === value.confirmation, { path: ["confirmation"], message: "Пароли не совпадают." });
type Values = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const { uid, token } = useSanitizedTokens(tokenNames);
  const [completed, setCompleted] = useState(false);
  const [formError, setFormError] = useState("");
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { new_password: "", confirmation: "" } });
  const mutation = useMutation({ mutationFn: confirmPasswordReset });
  const submit = handleSubmit(async ({ new_password }) => {
    setFormError("");
    try {
      await mutation.mutateAsync({ uid, token, new_password: new_password });
      setCompleted(true);
    } catch (error) {
      if (!applyApiFieldErrors(error, setError, ["new_password"])) setFormError(getApiErrorMessage(error, "Не удалось изменить пароль."));
    }
  });

  if (!uid || !token) return <AuthShell title="Недействительная ссылка" description="В ссылке восстановления отсутствуют необходимые данные."><FormAlert>Запросите новую ссылку восстановления пароля.</FormAlert><Link className="mt-5 inline-block font-medium underline" to="/forgot-password">Запросить ссылку</Link></AuthShell>;
  return <AuthShell title="Новый пароль" description="Создайте новый пароль для аккаунта." footer={<Link className="font-medium text-foreground underline" to="/login">Вернуться ко входу</Link>}>
    {completed ? <SuccessMessage>Пароль изменён. Теперь войдите с новым паролем.</SuccessMessage> : <form className="space-y-5" onSubmit={(event) => void submit(event)} noValidate>
      {formError ? <FormAlert>{formError}</FormAlert> : null}
      <FormField label="Новый пароль" type="password" autoComplete="new-password" registration={register("new_password")} error={errors.new_password} />
      <FormField label="Повторите пароль" type="password" autoComplete="new-password" registration={register("confirmation")} error={errors.confirmation} />
      <Button className="w-full" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Сохраняем…" : "Сохранить пароль"}</Button>
    </form>}
  </AuthShell>;
}