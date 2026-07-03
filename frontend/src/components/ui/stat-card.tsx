import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: string;
  className?: string;
}

export function StatCard({ label, value, icon: Icon, trend, className }: StatCardProps) {
  return (
    <div className={cn('card-surface group relative overflow-hidden p-5 transition-shadow hover:shadow-md hover:shadow-black/30', className)}>
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[#d26e41]/80 to-[#d26e41]/20" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
          {trend && <p className="mt-1 text-xs text-emerald-600">{trend}</p>}
        </div>
        {Icon && (
          <div className="rounded-xl bg-[#d26e41]/10 p-2.5 text-[#d26e41]">
            <Icon className="size-5" strokeWidth={1.75} />
          </div>
        )}
      </div>
    </div>
  );
}
