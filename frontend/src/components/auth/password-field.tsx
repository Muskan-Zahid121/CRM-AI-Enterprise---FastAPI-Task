import { useState } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";
import { AuthInput } from "./auth-input";
import { AuthLabel } from "./auth-label";
import { AuthFieldError } from "./auth-field-error";
import { cn } from "@/lib/utils";

interface PasswordFieldProps {
  id: string;
  label: string;
  hideLabel?: boolean;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  placeholder?: string;
  autoComplete?: string;
}

export function PasswordField({
  id,
  label,
  hideLabel = false,
  value,
  onChange,
  error,
  placeholder = "Enter your password",
  autoComplete = "current-password",
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="space-y-2">
      {!hideLabel && <AuthLabel htmlFor={id}>{label}</AuthLabel>}
      <div className="relative">
        <AuthInput
          id={id}
          icon={Lock}
          type={visible ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          aria-invalid={Boolean(error)}
          className={cn(
            "pr-10",
            error && "border-red-400/60 focus:border-red-400 focus:ring-red-400/20",
          )}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[#64748b] transition-colors hover:text-[#94a3b8]"
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      <AuthFieldError error={error} />
    </div>
  );
}
