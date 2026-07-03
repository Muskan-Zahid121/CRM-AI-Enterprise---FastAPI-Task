import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { dismissToast, subscribeToasts, type ToastItem } from '@/lib/toast';

const styles: Record<ToastItem['type'], string> = {
  error: 'border-red-500/30 bg-red-950/90 text-red-100',
  success: 'border-emerald-500/30 bg-emerald-950/90 text-emerald-100',
  info: 'border-sky-500/30 bg-sky-950/90 text-sky-100',
};

const icons: Record<ToastItem['type'], typeof AlertCircle> = {
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
};

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => subscribeToasts(setItems), []);

  if (items.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {items.map((item) => {
        const Icon = icons[item.type];
        return (
          <div
            key={item.id}
            role="alert"
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur-sm',
              styles[item.type],
            )}
          >
            <Icon className="mt-0.5 size-4 shrink-0" />
            <p className="flex-1 leading-snug">{item.message}</p>
            <button
              type="button"
              onClick={() => dismissToast(item.id)}
              className="shrink-0 rounded p-0.5 opacity-70 hover:opacity-100"
              aria-label="Dismiss"
            >
              <X className="size-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
