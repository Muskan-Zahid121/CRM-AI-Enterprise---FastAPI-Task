import { useState, type FormEvent } from 'react';
import { FileText, Search, Users } from 'lucide-react';
import { platformApi } from '@/api/platform';

export function GlobalSearchBar() {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<{
    customers: { id: number; name: string }[];
    documents: { content: string; document_id: number; score?: number }[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setOpen(true);
    try {
      const res = await platformApi.globalSearch(query.trim());
      setResults(res);
    } catch {
      setResults({ customers: [], documents: [] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative w-full max-w-md">
      <form onSubmit={handleSearch} className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search customers, documents..."
          className="input-dark pl-10"
        />
      </form>

      {open && query && (
        <>
          <button type="button" className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-label="Close search" />
          <div className="absolute right-0 z-50 mt-2 w-[min(100vw-2rem,28rem)] rounded-2xl border border-slate-700 bg-slate-900 p-4 shadow-xl shadow-black/40">
            {loading ? (
              <p className="text-sm text-slate-400">Searching...</p>
            ) : (
              <div className="space-y-4">
                {results?.customers.length ? (
                  <div>
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                      <Users className="size-3.5" /> Customers
                    </p>
                    <ul className="space-y-1">
                      {results.customers.map((c) => (
                        <li key={c.id} className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-200">{c.name}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {results?.documents.length ? (
                  <div>
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-500">
                      <FileText className="size-3.5" /> Documents
                    </p>
                    <ul className="space-y-1">
                      {results.documents.slice(0, 5).map((d, i) => (
                        <li key={i} className="rounded-lg bg-slate-800 px-3 py-2 text-xs text-slate-400 line-clamp-2">
                          {d.content.slice(0, 120)}...
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {!results?.customers.length && !results?.documents.length && (
                  <p className="text-sm text-slate-400">No results for &ldquo;{query}&rdquo;</p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
