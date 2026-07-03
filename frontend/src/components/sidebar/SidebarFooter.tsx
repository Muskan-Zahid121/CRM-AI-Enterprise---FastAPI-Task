import { useEffect, useState } from 'react';
import { LogOut } from 'lucide-react';
import { getStoredUser } from '@/lib/auth-storage';
import { cn } from '@/lib/utils';

interface SidebarFooterProps {
  onLogout: () => void;
  className?: string;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase() || 'U';
}

export function SidebarFooter({ onLogout, className }: SidebarFooterProps) {
  const [, refreshKey] = useState(0);
  const user = getStoredUser<{ name: string; email: string; role?: string }>();

  useEffect(() => {
    const onUpdate = () => refreshKey((v) => v + 1);
    window.addEventListener('auth-user-updated', onUpdate);
    return () => window.removeEventListener('auth-user-updated', onUpdate);
  }, []);

  if (!user) return null;

  const initials = getInitials(user.name);

  return (
    <div className={cn('mt-auto border-t border-slate-800 p-4', className)}>
      <div className="flex items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#d26e41] text-sm font-semibold text-white">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-100">{user.name}</p>
          <p className="truncate text-xs text-slate-500">{user.email}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onLogout}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2.5 text-sm font-medium text-slate-300 transition-colors hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400"
      >
        <LogOut className="size-4" />
        Sign out
      </button>
    </div>
  );
}
