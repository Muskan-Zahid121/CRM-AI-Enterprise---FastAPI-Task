interface AuthFieldErrorProps {
  error?: string;
}

export function AuthFieldError({ error }: AuthFieldErrorProps) {
  if (!error) return null;

  return (
    <p className="text-xs text-red-400" role="alert">
      {error}
    </p>
  );
}
