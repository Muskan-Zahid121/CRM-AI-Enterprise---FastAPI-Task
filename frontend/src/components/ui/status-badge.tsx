import { cn } from '@/lib/utils';

const palette: Record<string, string> = {
  active: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  pending: 'bg-amber-50 text-amber-700 ring-amber-200',
  completed: 'bg-slate-100 text-slate-600 ring-slate-200',
  new: 'bg-sky-50 text-sky-700 ring-sky-200',
  qualified: 'bg-violet-50 text-violet-700 ring-violet-200',
  proposal: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  negotiation: 'bg-orange-50 text-orange-700 ring-orange-200',
  closed_won: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  closed_lost: 'bg-red-50 text-red-600 ring-red-200',
  high: 'bg-red-50 text-red-700 ring-red-200',
  medium: 'bg-amber-50 text-amber-700 ring-amber-200',
  low: 'bg-slate-50 text-slate-600 ring-slate-200',
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const key = status.toLowerCase().replace(/\s+/g, '_');
  const isDark = className?.includes('dark-badge');
  const darkPalette: Record<string, string> = {
    active: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    draft: 'bg-slate-700/80 text-slate-300 ring-slate-600',
    pending: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    completed: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    failed: 'bg-red-500/15 text-red-300 ring-red-500/30',
    running: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
  };
  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset capitalize',
        isDark
          ? (darkPalette[key] ?? 'bg-slate-700/80 text-slate-300 ring-slate-600')
          : (palette[key] ?? 'bg-slate-50 text-slate-600 ring-slate-200'),
        className,
      )}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}
