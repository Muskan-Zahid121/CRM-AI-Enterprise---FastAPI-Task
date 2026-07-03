import { useEffect, useState, type FormEvent } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { AlertBanner } from '@/components/ui/alert-banner';
import { LoadingButton } from '@/components/ui/loading-button';
import { StatusBadge } from '@/components/ui/status-badge';
import { platformApi, type Deal } from '@/api/platform';

const STAGES = ['lead', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'];

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [pipeline, setPipeline] = useState<Record<string, number>>({});
  const [title, setTitle] = useState('');
  const [value, setValue] = useState('0');
  const [stage, setStage] = useState('lead');
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  async function load() {
    const [d, p] = await Promise.all([platformApi.listDeals(), platformApi.dealsPipeline()]);
    setDeals(d.deals);
    setPipeline(p.pipeline ?? {});
  }

  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      await platformApi.createDeal({ title, value: parseFloat(value), stage, probability: 50 });
      setTitle('');
      setValue('0');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setCreating(false);
    }
  }

  async function handleStageChange(dealId: number, newStage: string) {
    setUpdatingId(dealId);
    try {
      await platformApi.changeDealStage(dealId, newStage);
      await load();
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Deals Pipeline" subtitle="Track opportunities through sales stages" />
      <AlertBanner message={error} onDismiss={() => setError('')} />

      <div className="mb-6 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {STAGES.map((s) => (
          <div key={s} className="card-surface p-4 text-center transition-shadow hover:shadow-md">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{s.replace('_', ' ')}</p>
            <p className="mt-1 text-2xl font-semibold text-[#d26e41]">{pipeline[s] ?? 0}</p>
          </div>
        ))}
      </div>

      <form onSubmit={handleCreate} className="card-surface mb-6 grid gap-3 p-5 md:grid-cols-5">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Deal title" required className="input-dark md:col-span-2" />
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Value" type="number" className="input-dark" />
        <select value={stage} onChange={(e) => setStage(e.target.value)} className="input-dark">
          {STAGES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <LoadingButton type="submit" loading={creating} loadingText="Adding...">Add Deal</LoadingButton>
      </form>

      <div className="space-y-2">
        {deals.map((d) => (
          <div key={d.id} className="card-surface flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="font-medium text-slate-900">{d.title}</p>
              <p className="text-xs text-slate-500">{d.probability}% probability</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={d.stage}
                disabled={updatingId === d.id}
                onChange={(e) => handleStageChange(d.id, e.target.value)}
                className="input-dark h-9 py-0 text-xs disabled:opacity-50"
              >
                {STAGES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
              </select>
              <StatusBadge status={d.stage} />
              <p className="text-lg font-semibold text-[#d26e41]">${d.value.toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
