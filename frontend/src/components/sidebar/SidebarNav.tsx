import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { getActiveTabPath } from '@/lib/tabs';
import type { TabItem } from '@/components/sidebar/SectionTabs';

interface SidebarNavProps {
  tabs: TabItem[];
  onNavigate?: () => void;
}

export function SidebarNav({ tabs, onNavigate }: SidebarNavProps) {
  const location = useLocation();
  const activePath = getActiveTabPath(location.pathname, tabs);

  return (
    <nav aria-label="Main navigation" className="flex flex-col gap-0.5 px-3 py-2">
      {tabs.map((tab) => {
        const active = activePath === tab.path;
        const Icon = tab.icon;
        return (
          <Link
            key={tab.path}
            to={tab.path}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              active
                ? 'bg-[#d26e41]/15 text-[#d26e41] ring-1 ring-[#d26e41]/20'
                : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200',
            )}
          >
            <Icon className="size-4 shrink-0" strokeWidth={active ? 2.25 : 1.75} />
            <span className="truncate">{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
