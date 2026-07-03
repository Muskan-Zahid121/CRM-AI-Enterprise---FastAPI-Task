import { AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertBannerProps {
  message: string;
  variant?: 'error' | 'success' | 'info';
  onDismiss?: () => void;
  className?: string;
}

const styles = {
  error: 'border-red-500/30 bg-red-500/10 text-red-300',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  info: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
};

export function AlertBanner({ message, variant = 'error', onDismiss, className }: AlertBannerProps) {
  if (!message) return null;
  return (
    <div className={cn('mb-4 flex items-start gap-3 rounded-xl border p-3 text-sm', styles[variant], className)}>
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <p className="flex-1">{message}</p>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="shrink-0 opacity-60 hover:opacity-100" aria-label="Dismiss">
          <X className="size-4" />
        </button>
      )}
    </div>
  );
}
