import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

import { confirmEmailVerification } from "@/api/auth";
import { getApiErrorMessage } from "@/api/errors";
import { useRefreshSession, useSession } from "@/auth/session";
import { useSanitizedTokens } from "@/auth/tokens";
import { AuthShell, FormAlert, SuccessMessage } from "@/components/auth/auth-shell";

const tokenNames = ["token"] as const;

export function VerifyEmailPage() {
  const { token } = useSanitizedTokens(tokenNames);
  const session = useSession();
  const refreshSession = useRefreshSession();
  const started = useRef(false);
  const mutation = useMutation({ mutationFn: confirmEmailVerification });

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    void mutation.mutateAsync(token).then(() => refreshSession()).catch(() => undefined);
  }, [mutation, refreshSession, token]);

  return <AuthShell title="Подтверждение email" description="Проверяем ссылку подтверждения.">
    {!token ? <FormAlert>Ссылка подтверждения недействительна. Запросите новое письмо в кабинете.</FormAlert> : null}
    {token && mutation.isPending ? <p role="status" className="text-sm text-muted-foreground">Подтверждаем email…</p> : null}
    {mutation.isSuccess ? <><SuccessMessage>Email подтверждён.</SuccessMessage><Link className="mt-5 inline-block font-medium underline" to={session.data?.authenticated ? "/app" : "/login"}>{session.data?.authenticated ? "Вернуться в кабинет" : "Перейти ко входу"}</Link></> : null}
    {mutation.isError ? <><FormAlert>{getApiErrorMessage(mutation.error, "Не удалось подтвердить email.")}</FormAlert><p className="mt-4 text-sm text-muted-foreground">Если вы вошли, запросите новое письмо в кабинете.</p></> : null}
  </AuthShell>;
}