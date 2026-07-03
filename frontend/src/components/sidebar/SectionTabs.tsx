import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getActiveTabPath } from '@/lib/tabs';

export interface TabItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

interface SectionTabsProps {
  tabs: TabItem[];
}

export function SectionTabs({ tabs }: SectionTabsProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const activePath = getActiveTabPath(location.pathname, tabs);
  const activeTab = tabs.find((tab) => tab.path === activePath) ?? tabs[0];
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [menuOpen]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const ActiveIcon = activeTab.icon;

  return (
    <div className="w-full min-w-0 rounded-lg bg-slate-100 p-1">
      <nav aria-label="CRM sections">
        <div className="relative min-[1200px]:hidden" ref={menuRef}>
          <button
            type="button"
            aria-haspopup="listbox"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className="flex w-full items-center justify-between gap-3 rounded-md bg-white px-3 py-2.5 text-left text-sm font-medium text-[#d26e41]"
          >
            <span className="inline-flex min-w-0 items-center gap-2">
              <ActiveIcon className="size-4 shrink-0" aria-hidden />
              <span className="truncate">{activeTab.label}</span>
            </span>
            <ChevronDown
              className={cn('size-4 shrink-0 text-slate-400', menuOpen && 'rotate-180')}
              aria-hidden
            />
          </button>
          {menuOpen ? (
            <ul role="listbox" className="absolute z-40 mt-1 w-full rounded-lg border border-slate-200 bg-white p-1 shadow-md">
              {tabs.map((tab) => {
                const active = activePath === tab.path;
                const Icon = tab.icon;
                return (
                  <li key={tab.path} role="option" aria-selected={active}>
                    <button
                      type="button"
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm',
                        active ? 'bg-slate-100 font-medium text-[#d26e41]' : 'text-slate-600 hover:bg-slate-50',
                      )}
                      onClick={() => {
                        setMenuOpen(false);
                        navigate(tab.path);
                      }}
                    >
                      <Icon className="size-4 shrink-0" aria-hidden />
                      <span className="truncate">{tab.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>

        <div
          className="hidden w-full min-w-0 gap-1 min-[1200px]:grid"
          style={{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }}
        >
          {tabs.map((tab) => {
            const active = activePath === tab.path;
            const Icon = tab.icon;
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className={cn(
                  'inline-flex items-center justify-center gap-2 rounded-md px-3 py-2.5 text-sm font-medium',
                  active ? 'bg-white text-[#d26e41] shadow-sm' : 'text-slate-600 hover:text-[#d26e41]',
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden />
                <span className="truncate">{tab.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
