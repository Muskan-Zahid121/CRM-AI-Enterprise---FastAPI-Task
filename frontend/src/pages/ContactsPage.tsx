import { useEffect, useState, type FormEvent } from 'react';
import { Briefcase, ContactRound, Mail, Trash2, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { AlertBanner } from '@/components/ui/alert-banner';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingButton } from '@/components/ui/loading-button';
import { useConfirm } from '@/components/ui/confirm-modal';
import { platformApi, type Contact } from '@/api/platform';

function contactInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export default function ContactsPage() {
  const confirm = useConfirm();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function load() {
    const res = await platformApi.listContacts();
    setContacts(res.contacts);
  }

  useEffect(() => { load().catch((e) => setError(e.message)); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await platformApi.createContact({ name, email, title, is_primary: false });
      setName(''); setEmail(''); setTitle('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number, contactName: string) {
    const ok = await confirm({
      title: 'Delete contact',
      message: `Delete "${contactName}"? This action cannot be undone.`,
      confirmText: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingId(id);
    try {
      await platformApi.deleteContact(id);
      await load();
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Contacts" subtitle="People linked to your customer accounts" />
      <AlertBanner message={error} onDismiss={() => setError('')} />

      <form onSubmit={handleCreate} className="card-surface mb-6 grid gap-3 p-5 md:grid-cols-5">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" required className="input-dark" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" type="email" className="input-dark" />
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Job title" className="input-dark md:col-span-2" />
        <LoadingButton type="submit" loading={loading} loadingText="Saving...">Add Contact</LoadingButton>
      </form>

      {contacts.length === 0 ? (
        <EmptyState icon={ContactRound} title="No contacts yet" description="Add contacts to track relationships across accounts." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {contacts.map((c) => (
            <article
              key={c.id}
              className="card-surface group relative overflow-hidden transition-all hover:border-[#d26e41]/30 hover:shadow-lg hover:shadow-black/25"
            >
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[#d26e41]/80 via-[#d26e41]/40 to-transparent" />
              <div className="flex items-start gap-4 p-5">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#d26e41]/25 to-slate-800 text-sm font-bold text-[#d26e41] ring-1 ring-[#d26e41]/20">
                  {contactInitials(c.name) || '?'}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate font-semibold text-slate-100">{c.name}</h3>
                      {c.is_primary && (
                        <span className="mt-1 inline-flex rounded-full bg-[#d26e41]/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#d26e41]">
                          Primary
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDelete(c.id, c.name)}
                      disabled={deletingId === c.id}
                      className="rounded-lg p-1.5 text-slate-500 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100 disabled:opacity-50"
                      aria-label="Delete contact"
                    >
                      {deletingId === c.id ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
                    </button>
                  </div>

                  <div className="mt-3 space-y-2">
                    {c.title && (
                      <p className="flex items-center gap-2 text-sm text-slate-400">
                        <Briefcase className="size-3.5 shrink-0 text-slate-500" />
                        <span className="truncate">{c.title}</span>
                      </p>
                    )}
                    <p className="flex items-center gap-2 text-sm text-slate-400">
                      <Mail className="size-3.5 shrink-0 text-slate-500" />
                      <span className="truncate">{c.email ?? 'No email on file'}</span>
                    </p>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
