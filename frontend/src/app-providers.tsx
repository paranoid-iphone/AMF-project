import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { useEffect, type PropsWithChildren } from "react";

import type { SessionState } from "@/api/auth";
import { clearProjectQueries, sessionQueryKey } from "@/auth/session";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

export function SessionEventBridge() {
  const client = useQueryClient();
  useEffect(() => {
    const handleUnauthorized = () => {
      void clearProjectQueries(client);
      void client.cancelQueries({ queryKey: sessionQueryKey });
      client.setQueryData<SessionState>(sessionQueryKey, { authenticated: false, user: null });
    };
    globalThis.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => globalThis.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [client]);
  return null;
}

export function AppProviders({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}><SessionEventBridge />{children}</QueryClientProvider>;
}
