export const projectQueryKeys = {
  all: ["projects"] as const,
  list: (userId: number) => ["projects", userId, "list"] as const,
  detail: (userId: number, projectId: string) => ["projects", userId, "detail", projectId] as const,
};
