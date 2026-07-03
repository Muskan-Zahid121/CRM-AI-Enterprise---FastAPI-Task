import { useEffect, useState, type FormEvent } from 'react';
import { UserCheck } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { LoadingButton } from '@/components/ui/loading-button';
import { platformApi, type Lead } from '@/api/platform';
import { toast } from '@/lib/toast';

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [convertingId, setConvertingId] = useState<number | null>(null);

  async function load() {
    const res = await platformApi.listLeads();
    setLeads(res.leads);
  }

  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await platformApi.createLead({ name, company, stage: 'new', score: 0 });
      setName('');
      setCompany('');
      await load();
    } finally {
      setCreating(false);
    }
  }

  async function handleConvert(id: number) {
    setConvertingId(id);
    try {
      await platformApi.convertLead(id);
      toast.success('Lead converted to customer');
      await load();
    } catch {
      /* error toast from api client */
    } finally {
      setConvertingId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Leads" subtitle="Capture and convert prospects into customers" />
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      <form onSubmit={handleCreate} className="card-surface mb-4 grid gap-3 p-5 md:grid-cols-3">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Lead name" required className="input-dark" />
        <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company" className="input-dark" />
        <LoadingButton type="submit" loading={creating} loadingText="Adding...">Add Lead</LoadingButton>
      </form>
      <div className="space-y-2">
        {leads.map((l) => (
          <div key={l.id} className="card-surface flex items-center justify-between p-4">
            <div>
              <p className="font-medium text-slate-900">{l.name}</p>
              <p className="text-xs text-slate-500">{l.company ?? '—'} · {l.stage}</p>
            </div>
            {l.stage !== 'converted' && (
              <LoadingButton
                variant="secondary"
                className="h-9 px-3 text-xs"
                loading={convertingId === l.id}
                loadingText="Converting..."
                onClick={() => handleConvert(l.id)}
              >
                <UserCheck className="size-3.5" />
                Convert
              </LoadingButton>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
