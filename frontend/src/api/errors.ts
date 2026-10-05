import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { ApiError } from "@/api/auth";

const messages: Record<string, string> = {
  invalid_credentials: "Неверный email или пароль.",
  invalid_invitation: "Приглашение недействительно или больше недоступно.",
  invalid_or_expired_token: "Ссылка недействительна или срок её действия истёк.",
  not_authenticated: "Войдите, чтобы продолжить.",
  csrf_failed: "Сессия безопасности устарела. Обновите страницу и повторите попытку.",
  rate_limited: "Слишком много попыток. Повторите позже.",
  validation_error: "Проверьте введённые данные.",
  unexpected_error: "Не удалось выполнить запрос. Повторите позже.",
};

export function getApiErrorMessage(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback;
  const message = messages[error.code] ?? fallback;
  return error.code === "rate_limited" && error.retryAfter
    ? `${message} Доступно через ${error.retryAfter} сек.`
    : message;
}

export function applyApiFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  allowedFields: readonly Path<T>[],
) {
  if (!(error instanceof ApiError) || !error.fields) return false;
  let applied = false;
  for (const field of allowedFields) {
    const items = error.fields[field];
    if (items?.[0]) {
      setError(field, { type: "server", message: items[0].message });
      applied = true;
    }
  }
  return applied;
}