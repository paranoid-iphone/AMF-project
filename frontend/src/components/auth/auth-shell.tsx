import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function AuthShell({ title, description, children, footer }: { title: string; description: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-5 py-10">
      <section className="w-full max-w-md rounded-lg border bg-card p-6 shadow-sm sm:p-8" aria-labelledby="auth-title">
        <Link to="/status" className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground">
          AMF
        </Link>
        <h1 id="auth-title" className="mt-4 text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        <div className="mt-7">{children}</div>
        {footer ? <div className="mt-6 border-t pt-5 text-sm text-muted-foreground">{footer}</div> : null}
      </section>
    </main>
  );
}

export function FormAlert({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{children}</div>;
}

export function SuccessMessage({ children }: { children: ReactNode }) {
  return <div role="status" className="rounded-md border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900">{children}</div>;
}