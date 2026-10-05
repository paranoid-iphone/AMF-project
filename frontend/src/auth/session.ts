import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import { getSession, type SessionState } from "@/api/auth";
import { projectQueryKeys } from "@/api/project-query-keys";

export const sessionQueryKey = ["auth", "session"] as const;

export async function clearProjectQueries(queryClient: QueryClient) {
  const cancellation = queryClient.cancelQueries({ queryKey: projectQueryKeys.all });
  queryClient.removeQueries({ queryKey: projectQueryKeys.all });
  await cancellation;
}

export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: getSession,
    staleTime: 30_000,
  });
}

export function useRefreshSession() {
  const queryClient = useQueryClient();
  return () => queryClient.fetchQuery({ queryKey: sessionQueryKey, queryFn: getSession });
}

export function useSetAnonymousSession() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.setQueryData<SessionState>(sessionQueryKey, {
      authenticated: false,
      user: null,
    });
}
