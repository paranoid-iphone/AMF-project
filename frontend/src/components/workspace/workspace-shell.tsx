import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { logout } from "@/api/auth";
import { getApiErrorMessage } from "@/api/errors";
import { clearProjectQueries, useRefreshSession, useSession, useSetAnonymousSession } from "@/auth/session";
import { FormAlert } from "@/components/auth/auth-shell";
import { Button } from "@/components/button";
import { EmailVerificationBanner } from "@/components/workspace/email-verification-banner";

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const session = useSession();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setAnonymous = useSetAnonymousSession();
  const refreshSession = useRefreshSession();
  const logoutMutation = useMutation({ mutationFn: logout });

  if (!session.data?.user) return null;
  const user = session.data.user;

  async function handleLogout() {
    try {
      await logoutMutation.mutateAsync();
      await clearProjectQueries(queryClient);
      setAnonymous();
      void navigate("/login", { replace: true });
    } catch (error) {
      if (error instanceof Error && "code" in error && error.code === "not_authenticated") {
        await clearProjectQueries(queryClient);
        setAnonymous();
        void navigate("/login", { replace: true });
        return;
      }
      await refreshSession();
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
      {!user.email_verified ? <EmailVerificationBanner /> : null}
      {logoutMutation.isError ? <div className="mb-6"><FormAlert>{getApiErrorMessage(logoutMutation.error, "Не удалось выйти из аккаунта.")}</FormAlert></div> : null}
      {children}
    </div>
  </main>;
}
