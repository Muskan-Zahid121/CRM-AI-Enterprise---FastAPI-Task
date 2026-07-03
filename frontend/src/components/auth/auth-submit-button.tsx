import { Loader2 } from 'lucide-react';

interface AuthSubmitButtonProps {
  loading: boolean;
  label: string;
  loadingLabel: string;
}

export function AuthSubmitButton({ loading, label, loadingLabel }: AuthSubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#d26e41] text-sm font-semibold text-white transition-colors hover:bg-[#e16e4f] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {loading ? loadingLabel : label}
    </button>
  );
}
