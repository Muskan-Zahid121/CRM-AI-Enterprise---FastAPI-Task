import { useEffect, useState } from 'react';
import { Briefcase, CheckSquare, DollarSign, Users, Activity } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { StatCard } from '@/components/ui/stat-card';
import { AlertBanner } from '@/components/ui/alert-banner';
import { StatusBadge } from '@/components/ui/status-badge';
import { platformApi, type ActivityItem, type DashboardOverview } from '@/api/platform';

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([platformApi.dashboard(), platformApi.dashboardActivity()])
      .then(([d, a]) => {
        setData(d);
        setActivity(a.activity);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Enterprise AI Sales CRM overview" />
      <AlertBanner message={error} onDismiss={() => setError('')} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Customers" value={data?.customers ?? '—'} icon={Users} />
        <StatCard label="Open Deals" value={data?.open_deals ?? '—'} icon={Briefcase} />
        <StatCard label="Pending Tasks" value={data?.pending_tasks ?? '—'} icon={CheckSquare} />
        <StatCard label="Pipeline Value" value={data ? `$${data.pipeline_value.toLocaleString()}` : '—'} icon={DollarSign} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="card-surface p-5 lg:col-span-2">
          <h2 className="font-semibold text-slate-900">Recent Deals</h2>
          <ul className="mt-4 space-y-2">
            {data?.recent_deals?.length ? data.recent_deals.map((d) => (
              <li key={d.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm">
                <div>
                  <span className="font-medium text-slate-900">{d.title}</span>
                  <StatusBadge status={d.stage} className="ml-2" />
                </div>
                <span className="font-semibold text-[#d26e41]">${d.value.toLocaleString()}</span>
              </li>
            )) : <li className="text-sm text-slate-500">No deals yet</li>}
          </ul>
        </section>

        <section className="card-surface p-5">
          <h2 className="flex items-center gap-2 font-semibold text-slate-900">
            <Activity className="size-4 text-[#d26e41]" /> Activity
          </h2>
          <ul className="mt-4 space-y-2">
            {activity.length ? activity.slice(0, 8).map((a) => (
              <li key={a.id} className="rounded-lg border border-slate-100 px-3 py-2 text-xs text-slate-600">
                <span className="font-medium text-slate-800">{a.type}</span>
                <p className="mt-0.5">{a.description}</p>
              </li>
            )) : <li className="text-sm text-slate-500">No recent activity</li>}
          </ul>
        </section>
      </div>

      <section className="card-surface mt-6 p-5">
        <h2 className="font-semibold text-slate-900">Recent Tasks</h2>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {data?.recent_tasks?.length ? data.recent_tasks.map((t) => (
            <li key={t.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm">
              <span className="text-slate-900">{t.title}</span>
              <StatusBadge status={t.status} />
            </li>
          )) : <li className="text-sm text-slate-500">No tasks yet</li>}
        </ul>
      </section>
    </div>
  );
}
