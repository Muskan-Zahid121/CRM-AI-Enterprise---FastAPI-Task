import { useEffect, useState, type FormEvent } from 'react';
import { Trash2, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { AlertBanner } from '@/components/ui/alert-banner';
import { StatusBadge } from '@/components/ui/status-badge';
import { LoadingButton } from '@/components/ui/loading-button';
import { useConfirm } from '@/components/ui/confirm-modal';
import { platformApi, type Customer } from '@/api/platform';

export default function CustomersPage() {
  const confirm = useConfirm();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function load(q?: string) {
    const res = await platformApi.listCustomers(q);
    setCustomers(res.customers);
  }

  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await platformApi.createCustomer({ name, email, company, status: 'active' });
      setName(''); setEmail(''); setCompany('');
      await load(search);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number, customerName: string) {
    const ok = await confirm({
      title: 'Delete customer',
      message: `Delete "${customerName}"? This action cannot be undone.`,
      confirmText: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingId(id);
    try {
      await platformApi.deleteCustomer(id);
      await load(search);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Customers" subtitle="Manage customer accounts and relationships" />
      <AlertBanner message={error} onDismiss={() => setError('')} />

      <form onSubmit={handleCreate} className="card-surface mb-6 grid gap-3 p-5 md:grid-cols-4">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" required className="input-dark" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" className="input-dark" />
        <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company" className="input-dark" />
        <LoadingButton type="submit" loading={loading} loadingText="Saving...">Add Customer</LoadingButton>
      </form>

      <div className="mb-4 flex gap-2">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customers" className="input-dark flex-1" />
        <LoadingButton
          variant="secondary"
          loading={searching}
          loadingText="Searching..."
          onClick={() => {
            setSearching(true);
            load(search).catch((e) => setError(e.message)).finally(() => setSearching(false));
          }}
        >
          Search
        </LoadingButton>
      </div>

      <div className="card-surface overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
            <tr>
              <th className="p-3 text-left font-medium">Name</th>
              <th className="p-3 text-left font-medium">Email</th>
              <th className="p-3 text-left font-medium">Company</th>
              <th className="p-3 text-left font-medium">Status</th>
              <th className="p-3 w-12" />
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id} className="group border-b border-slate-100 hover:bg-slate-50/50">
                <td className="p-3 font-medium text-slate-900">{c.name}</td>
                <td className="p-3 text-slate-600">{c.email ?? '—'}</td>
                <td className="p-3 text-slate-600">{c.company ?? '—'}</td>
                <td className="p-3"><StatusBadge status={c.status} /></td>
                <td className="p-3">
                  <button type="button" onClick={() => handleDelete(c.id, c.name)} disabled={deletingId === c.id} className="rounded-lg p-1.5 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 disabled:opacity-50" aria-label="Delete">
                    {deletingId === c.id ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
