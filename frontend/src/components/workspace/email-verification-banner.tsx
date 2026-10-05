import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { requestEmailVerification } from "@/api/auth";
import { getApiErrorMessage } from "@/api/errors";
import { Button } from "@/components/button";

export function EmailVerificationBanner() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const resend = useMutation({ mutationFn: requestEmailVerification });

  async function handleResend() {
    setError("");
    setMessage("");
    try {
      await resend.mutateAsync();
      setMessage("Письмо отправлено. Проверьте почту.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Не удалось отправить письмо."));
    }
  }

  return <section className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-5 text-amber-950" aria-labelledby="verification-title">
    <h2 id="verification-title" className="font-semibold">Подтвердите email</h2>
    <p className="mt-1 text-sm leading-6">Подтверждение email потребуется, чтобы активировать проект.</p>
    <Button className="mt-4 bg-amber-900 text-white hover:bg-amber-800" onClick={() => void handleResend()} disabled={resend.isPending}>{resend.isPending ? "Отправляем…" : "Отправить письмо повторно"}</Button>
    <div className="mt-3">{message ? <p role="status" className="text-sm">{message}</p> : null}{error ? <p role="alert" className="text-sm">{error}</p> : null}</div>
  </section>;
}
