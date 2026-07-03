import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/50 px-6 py-12 text-center">
      <div className="rounded-full bg-slate-800 p-3 ring-1 ring-slate-700">
        <Icon className="size-6 text-slate-500" strokeWidth={1.5} />
      </div>
      <p className="mt-4 text-sm font-medium text-slate-300">{title}</p>
      {description && <p className="mt-1 max-w-sm text-xs text-slate-500">{description}</p>}
    </div>
  );
}
