import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useSession } from "@/auth/session";

function LoadingSession() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6" role="status" aria-live="polite">
      <p className="text-muted-foreground">Проверяем сессию…</p>
    </main>
  );
}

function SessionFailure() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6" role="alert">
      <p className="text-destructive">Не удалось проверить сессию. Обновите страницу.</p>
    </main>
  );
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const session = useSession();
  const location = useLocation();
  if (session.isPending) return <LoadingSession />;
  if (session.isError) return <SessionFailure />;
  if (!session.data.authenticated) {
    const returnTo = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?returnTo=${encodeURIComponent(returnTo)}`} replace />;
  }
  return children;
}

export function AnonymousOnly({ children }: { children: ReactNode }) {
  const session = useSession();
  if (session.isPending) return <LoadingSession />;
  if (session.isError) return <SessionFailure />;
  if (session.data.authenticated) return <Navigate to="/app" replace />;
  return children;
}

export function SessionReady({ children }: { children: ReactNode }) {
  const session = useSession();
  if (session.isPending) return <LoadingSession />;
  if (session.isError) return <SessionFailure />;
  return children;
}

export function RootRedirect() {
  const session = useSession();
  if (session.isPending) return <LoadingSession />;
  if (session.isError) return <SessionFailure />;
  return <Navigate to={session.data.authenticated ? "/app" : "/login"} replace />;
}