import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSidebar } from '@/components/sidebar/sidebar-context';
import { cn } from '@/lib/utils';

interface AppHeaderProps {
  className?: string;
}

export function AppHeader({ className }: AppHeaderProps) {
  const { isOpen, toggle } = useSidebar();

  return (
    <div className={cn('flex items-center gap-3 px-3 py-3 sm:px-6 lg:px-8', className)}>
      {!isOpen ? (
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 text-slate-300 hover:bg-slate-800 hover:text-slate-100 lg:hidden"
          onClick={toggle}
          aria-label="Open sidebar"
        >
          <Menu className="size-5" />
        </Button>
      ) : null}
    </div>
  );
}
