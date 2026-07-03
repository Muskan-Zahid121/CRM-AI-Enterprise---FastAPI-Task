import { Outlet } from 'react-router-dom';
import {
  BookOpen,
  Briefcase,
  ContactRound,
  GitBranch,
  LayoutDashboard,
  Mail,
  MessageSquare,
  Settings,
  UserPlus,
  Users,
  CheckSquare,
  Video,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { clearAuthSession } from '@/lib/auth-storage';
import { SidebarProvider, useSidebar } from '@/components/sidebar/sidebar-context';
import { type TabItem } from '@/components/sidebar/SectionTabs';
import { SidebarNav } from '@/components/sidebar/SidebarNav';
import { SidebarFooter } from '@/components/sidebar/SidebarFooter';
import { AppHeader } from '@/components/layout/AppHeader';

const tabs: TabItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/customers', label: 'Customers', icon: Users },
  { path: '/contacts', label: 'Contacts', icon: ContactRound },
  { path: '/leads', label: 'Leads', icon: UserPlus },
  { path: '/deals', label: 'Deals', icon: Briefcase },
  { path: '/tasks', label: 'Tasks', icon: CheckSquare },
  { path: '/meetings', label: 'Meetings', icon: Video },
  { path: '/workflows', label: 'Workflows', icon: GitBranch },
  { path: '/knowledge', label: 'Knowledge Base', icon: BookOpen },
  { path: '/chat', label: 'AI Chat', icon: MessageSquare },
  { path: '/email', label: 'Email', icon: Mail },
  { path: '/settings', label: 'Settings', icon: Settings },
];

interface Props {
  onLogout: () => void;
}

function AppLayoutInner({ onLogout }: Props) {
  const { isOpen, close } = useSidebar();

  function handleLogout() {
    clearAuthSession();
    onLogout();
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {isOpen ? (
        <button
          type="button"
          aria-label="Close sidebar overlay"
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={close}
        />
      ) : null}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex h-full w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-900 transition-transform lg:static lg:w-72 lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        <div className="shrink-0 border-b border-slate-800 px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#d26e41]/90">CRM AI Platform</p>
          <h1 className="mt-1 text-lg font-semibold text-slate-100">Sales Assistant</h1>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto brand-scrollbar">
          <SidebarNav tabs={tabs} onNavigate={close} />
        </div>

        <SidebarFooter onLogout={handleLogout} />
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <header className="shrink-0 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm lg:hidden">
          <div className="mx-auto flex max-w-[1600px] items-center px-4 py-3 sm:px-6 lg:px-8">
            <AppHeader />
          </div>
        </header>

        <main className="brand-scrollbar mx-auto flex min-h-0 w-full max-w-[1600px] flex-1 flex-col overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function AppLayout(props: Props) {
  return (
    <SidebarProvider>
      <AppLayoutInner {...props} />
    </SidebarProvider>
  );
}
