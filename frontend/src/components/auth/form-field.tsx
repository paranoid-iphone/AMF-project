import type { InputHTMLAttributes } from "react";
import type { FieldError, UseFormRegisterReturn } from "react-hook-form";

import { Input } from "./input";

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  registration: UseFormRegisterReturn;
  error?: FieldError;
  hint?: string;
}

export function FormField({ label, registration, error, hint, id, ...props }: FormFieldProps) {
  const inputId = id ?? registration.name;
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;
  const describedBy = [hint ? hintId : "", error ? errorId : ""].filter(Boolean).join(" ");

  return (
    <div className="space-y-2">
      <label htmlFor={inputId} className="text-sm font-medium">
        {label}
      </label>
      <Input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy || undefined}
        {...registration}
        {...props}
      />
      {hint ? <p id={hintId} className="text-sm text-muted-foreground">{hint}</p> : null}
      {error ? <p id={errorId} className="text-sm text-destructive">{error.message}</p> : null}
    </div>
  );
}