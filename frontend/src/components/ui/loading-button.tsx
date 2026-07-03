import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  loadingText?: string;
  variant?: 'primary' | 'secondary';
}

export function LoadingButton({
  loading = false,
  loadingText,
  variant = 'primary',
  children,
  className,
  disabled,
  type = 'button',
  ...props
}: LoadingButtonProps) {
  return (
    <button
      type={type}
      {...props}
      disabled={disabled || loading}
      className={cn(
        variant === 'primary' ? 'btn-primary' : 'btn-secondary',
        'inline-flex flex-row items-center justify-center gap-2 whitespace-nowrap [&_svg]:shrink-0',
        className,
      )}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {loading ? (loadingText ?? 'Loading...') : children}
    </button>
  );
}
