import type { TabItem } from '@/components/sidebar/SectionTabs';

export function getActiveTabPath(pathname: string, tabs: TabItem[]): string {
  const match = tabs.find(
    (tab) => pathname === tab.path || pathname.startsWith(`${tab.path}/`),
  );
  return match?.path ?? tabs[0]?.path ?? pathname;
}
