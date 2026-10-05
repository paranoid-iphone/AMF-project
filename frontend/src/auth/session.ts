import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getSession, type SessionState } from "@/api/auth";

export const sessionQueryKey = ["auth", "session"] as const;

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