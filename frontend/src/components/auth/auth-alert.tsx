interface AuthAlertProps {
  message: string;
  variant?: "error" | "success" | "info";
}

export function AuthAlert({ message, variant = "error" }: AuthAlertProps) {
  const styles = {
    error: "border-red-400/30 bg-red-400/10 text-red-300",
    success: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
    info: "border-[#d26e41]/20 bg-[#d26e41]/10 text-[#e8a07a]",
  };

  return (
    <div
      className={`rounded-xl border px-3 py-2.5 text-sm ${styles[variant]}`}
      role="alert"
    >
      {message}
    </div>
  );
}
