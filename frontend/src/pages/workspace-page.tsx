import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { logout, requestEmailVerification } from "@/api/auth";
import { getApiErrorMessage } from "@/api/errors";
import { useRefreshSession, useSession, useSetAnonymousSession } from "@/auth/session";
import { FormAlert, SuccessMessage } from "@/components/auth/auth-shell";
import { Button } from "@/components/button";

export function WorkspacePage() {
  const session = useSession();
  const navigate = useNavigate();
  const setAnonymous = useSetAnonymousSession();
  const refreshSession = useRefreshSession();
  const [resendMessage, setResendMessage] = useState("");
  const [resendError, setResendError] = useState("");
  const resend = useMutation({ mutationFn: requestEmailVerification });
  const logoutMutation = useMutation({ mutationFn: logout });
  const user = session.data?.user;

  if (!user) return null;

  async function handleLogout() {
    try {
      await logoutMutation.mutateAsync();
      setAnonymous();
      void navigate("/login", { replace: true });
    } catch {
      await refreshSession();
    }
  }

  async function handleResend() {
    setResendError("");
    setResendMessage("");
    try {
      await resend.mutateAsync();
      setResendMessage("Письмо отправлено. Проверьте почту.");
    } catch (error) {
      setResendError(getApiErrorMessage(error, "Не удалось отправить письмо."));
    }
  }

  return <main className="min-h-screen bg-muted/40">
    <header className="border-b bg-card">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-4">
        <div><p className="font-bold">AMF</p><p className="text-sm text-muted-foreground">{user.email}</p></div>
        <Button className="bg-background text-foreground ring-1 ring-border hover:bg-muted" onClick={() => void handleLogout()} disabled={logoutMutation.isPending}>{logoutMutation.isPending ? "Выходим…" : "Выйти"}</Button>
      </div>
    </header>
    <div className="mx-auto max-w-5xl px-5 py-8">
      {!user.email_verified ? <section className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-5 text-amber-950" aria-labelledby="verification-title">
        <h2 id="verification-title" className="font-semibold">Подтвердите email</h2>
        <p className="mt-1 text-sm leading-6">Кабинет уже доступен, но для будущей отправки проекта потребуется подтверждение email.</p>
        <Button className="mt-4 bg-amber-900 text-white hover:bg-amber-800" onClick={() => void handleResend()} disabled={resend.isPending}>{resend.isPending ? "Отправляем…" : "Отправить письмо повторно"}</Button>
        <div className="mt-3">{resendMessage ? <SuccessMessage>{resendMessage}</SuccessMessage> : null}{resendError ? <FormAlert>{resendError}</FormAlert> : null}</div>
      </section> : null}
      <section className="rounded-lg border bg-card p-6 shadow-sm" aria-labelledby="workspace-title">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Приватный кабинет</p>
        <h1 id="workspace-title" className="mt-2 text-3xl font-bold">Рабочее пространство</h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">Основа аккаунта готова. Проекты и анкеты появятся в следующих функциональных этапах.</p>
      </section>
    </div>
  </main>;
}