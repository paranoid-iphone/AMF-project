import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/api/health";
import { Button } from "@/components/button";

export function StatusPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <section
        className="w-full max-w-2xl rounded-lg border bg-card p-8 text-card-foreground shadow-sm sm:p-12"
        aria-labelledby="page-title"
      >
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Application foundation
        </p>
        <h1 id="page-title" className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
          AMF application
        </h1>
        <p className="mt-4 max-w-xl text-base leading-7 text-muted-foreground">
          The foundation is connected to the AMF API and ready for future product features.
        </p>

        <div className="mt-10 rounded-md border bg-background p-5">
          <h2 className="text-lg font-semibold">Service status</h2>

          {healthQuery.isPending ? (
            <div className="mt-4 flex items-center gap-3" role="status" aria-live="polite">
              <span
                className="h-3 w-3 animate-pulse rounded-full bg-muted-foreground"
                aria-hidden="true"
              />
              <span>Checking API availability…</span>
            </div>
          ) : null}

          {healthQuery.isSuccess ? (
            <div className="mt-4 flex items-start gap-3" role="status" aria-live="polite">
              <span className="mt-1 h-3 w-3 rounded-full bg-emerald-600" aria-hidden="true" />
              <div>
                <p className="font-semibold text-emerald-800">All systems operational</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  API and database checks completed successfully.
                </p>
              </div>
            </div>
          ) : null}

          {healthQuery.isError ? (
            <div className="mt-4" role="alert">
              <div className="flex items-start gap-3">
                <span className="mt-1 h-3 w-3 rounded-full bg-destructive" aria-hidden="true" />
                <div>
                  <p className="font-semibold text-destructive">Service unavailable</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    The API health check could not be completed. Try again shortly.
                  </p>
                </div>
              </div>
              <Button className="mt-5" onClick={() => void healthQuery.refetch()}>
                Retry health check
              </Button>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
