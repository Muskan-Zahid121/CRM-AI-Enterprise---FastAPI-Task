import { useEffect, useRef, useState, type FormEvent } from 'react';
import { FileText, Loader2, Trash2, Upload } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingButton } from '@/components/ui/loading-button';
import { useConfirm } from '@/components/ui/confirm-modal';
import { platformApi, type DocumentItem } from '@/api/platform';
import { toast } from '@/lib/toast';

const ACCEPT = '.txt,.md,.csv,.pdf,.docx';

export default function KnowledgePage() {
  const confirm = useConfirm();
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [stats, setStats] = useState<{ total_chunks?: number; indexed_documents?: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    const [d, s] = await Promise.all([
      platformApi.listDocuments(),
      platformApi.ragStats() as Promise<{ stats: { total_chunks: number; indexed_documents: number } }>,
    ]);
    setDocs(d.documents);
    setStats(s.stats);
  }

  useEffect(() => {
    load().catch(() => {});
  }, []);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0] ?? null;
    setFile(picked);
    if (picked && !title.trim()) {
      setTitle(picked.name.replace(/\.[^.]+$/, ''));
    }
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file && !content.trim()) {
      toast.error('Choose a file or paste document content.');
      return;
    }

    setUploading(true);
    try {
      if (file) {
        const res = await platformApi.uploadKnowledgeFile(file, title || undefined);
        toast.success(`Indexed ${res.document.chunks} chunks from "${res.document.title}"`);
      } else {
        if (!title.trim()) {
          toast.error('Please enter a document title.');
          return;
        }
        const res = await platformApi.uploadKnowledge({ title, content });
        toast.success(`Indexed ${res.document.chunks} chunks from "${title}"`);
      }
      setTitle('');
      setContent('');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await load();
    } catch {
      /* error toast from api client */
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number, docTitle: string) {
    const ok = await confirm({
      title: 'Delete document',
      message: `Delete "${docTitle}" and all its indexed chunks? This cannot be undone.`,
      confirmText: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingId(id);
    try {
      await platformApi.deleteDocument(id);
      toast.success(`Deleted "${docTitle}"`);
      await load();
    } catch {
      /* error toast from api client */
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Knowledge Base"
        subtitle={`Upload & manage RAG documents — ask about them in Chat. ${stats?.total_chunks ?? 0} chunks · ${stats?.indexed_documents ?? 0} docs indexed`}
      />

      <div className="mb-4 rounded-xl border border-violet-500/20 bg-violet-500/5 px-4 py-3 text-sm text-slate-400">
        Documents uploaded here are vectorized for AI search. Go to <strong className="text-violet-300">Chat</strong> and ask
        e.g. <em className="text-slate-300">"What does our pricing document say?"</em> — the knowledge agent will answer from your uploads.
      </div>

      <form onSubmit={handleUpload} className="card-surface mb-6 space-y-4 p-5">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-400">Document title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enterprise CRM Pricing"
            className="input-dark w-full"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-400">Upload file</label>
          <div
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-600 bg-slate-800/40 px-4 py-8 transition-colors hover:border-[#d26e41]/50 hover:bg-slate-800/60"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mb-2 size-8 text-[#d26e41]" />
            <p className="text-sm text-slate-300">{file ? file.name : 'PDF, DOCX, TXT, MD, or CSV'}</p>
            <p className="mt-1 text-xs text-slate-500">Max 10 MB — chunked & vectorized automatically</p>
            <input ref={fileInputRef} type="file" accept={ACCEPT} className="hidden" onChange={handleFileChange} />
          </div>
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-slate-700" /></div>
          <div className="relative flex justify-center text-xs uppercase"><span className="bg-slate-900 px-2 text-slate-500">or paste text</span></div>
        </div>

        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste policy, pricing, or product content..."
          rows={4}
          className="input-dark w-full"
        />

        <LoadingButton type="submit" loading={uploading} loadingText="Uploading & indexing...">
          <FileText className="mr-2 size-4" />
          Upload & Index
        </LoadingButton>
      </form>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Uploaded documents</h2>
        {docs.length === 0 ? (
          <EmptyState icon={FileText} title="No documents yet" description="Upload files above. Then ask questions in Chat." />
        ) : (
          <div className="space-y-2">
            {docs.map((d) => (
              <div key={d.id} className="card-surface flex items-center justify-between gap-4 p-4">
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-200">{d.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {d.indexed ? `${d.chunk_count} chunks indexed` : 'Not indexed'}
                    {' · '}ID {d.id}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(d.id, d.title)}
                  disabled={deletingId === d.id}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/20 disabled:opacity-50"
                >
                  {deletingId === d.id ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
