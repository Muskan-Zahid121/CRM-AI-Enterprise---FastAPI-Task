import { useEffect, useState, type FormEvent } from 'react';
import { Calendar, ChevronDown, ChevronUp, Pencil, Sparkles, Trash2, X } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingButton } from '@/components/ui/loading-button';
import { useConfirm } from '@/components/ui/confirm-modal';
import { platformApi, type Meeting } from '@/api/platform';
import { toast } from '@/lib/toast';

export default function MeetingsPage() {
  const confirm = useConfirm();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [title, setTitle] = useState('');
  const [transcript, setTranscript] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [summarizing, setSummarizing] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function load() {
    const res = await platformApi.listMeetings();
    setMeetings(res.meetings);
  }

  useEffect(() => {
    load().catch(() => {});
  }, []);

  function resetForm() {
    setTitle('');
    setTranscript('');
    setEditingId(null);
  }

  function startEdit(m: Meeting) {
    setEditingId(m.id);
    setTitle(m.title);
    setTranscript(m.transcript ?? '');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await platformApi.updateMeeting(editingId, { title, transcript });
        toast.success('Meeting updated');
      } else {
        await platformApi.createMeeting({ title, transcript });
        toast.success('Meeting saved');
      }
      resetForm();
      await load();
    } catch {
      /* error toast from api client */
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number, meetingTitle: string) {
    const ok = await confirm({
      title: 'Delete meeting',
      message: `Delete "${meetingTitle}"? The transcript and summary will be permanently removed.`,
      confirmText: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingId(id);
    try {
      await platformApi.deleteMeeting(id);
      toast.success('Meeting deleted');
      if (editingId === id) resetForm();
      if (expandedId === id) setExpandedId(null);
      await load();
    } catch {
      /* error toast from api client */
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSummarize(id: number) {
    setSummarizing(id);
    try {
      await platformApi.summarizeMeeting(id);
      toast.success('AI summary generated');
      await load();
      setExpandedId(id);
    } catch {
      /* error toast from api client */
    } finally {
      setSummarizing(null);
    }
  }

  return (
    <div>
      <PageHeader title="Meetings" subtitle="Save transcripts — summarize & query them from Chat" />

      <form onSubmit={handleSubmit} className="card-surface mb-6 space-y-4 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">
            {editingId ? 'Edit meeting' : 'New meeting template'}
          </h2>
          {editingId && (
            <button type="button" onClick={resetForm} className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300">
              <X className="size-3.5" /> Cancel edit
            </button>
          )}
        </div>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Meeting title — e.g. Enterprise CRM Demo - ABC Technologies"
          required
          className="input-dark w-full"
        />
        <textarea
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Paste meeting transcript or notes..."
          rows={5}
          className="input-dark w-full min-h-[120px] py-3"
        />
        <LoadingButton type="submit" loading={saving} loadingText={editingId ? 'Updating...' : 'Saving...'}>
          {editingId ? 'Update Meeting' : 'Save Meeting'}
        </LoadingButton>
      </form>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Saved meetings</h2>
        {meetings.length === 0 ? (
          <EmptyState icon={Calendar} title="No meetings yet" description="Save a transcript above, then generate an AI summary." />
        ) : (
          <div className="space-y-3">
            {meetings.map((m) => {
              const expanded = expandedId === m.id;
              const preview = m.transcript?.slice(0, 160) ?? 'No transcript';
              return (
                <article key={m.id} className="card-surface overflow-hidden">
                  <div className="flex flex-wrap items-start justify-between gap-3 p-5">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-slate-100">{m.title}</h3>
                      <p className="mt-1 text-xs text-slate-500">
                        {m.created_at ? new Date(m.created_at).toLocaleDateString() : '—'}
                        {m.summary ? ' · Summary ready' : ' · No summary yet'}
                      </p>
                      {!expanded && (
                        <p className="mt-2 text-sm text-slate-400 line-clamp-2">{preview}{m.transcript && m.transcript.length > 160 ? '...' : ''}</p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setExpandedId(expanded ? null : m.id)}
                        className="btn-secondary h-9 px-3 text-xs"
                      >
                        {expanded ? <ChevronUp className="mr-1 size-3.5" /> : <ChevronDown className="mr-1 size-3.5" />}
                        {expanded ? 'Hide' : 'View'}
                      </button>
                      <button type="button" onClick={() => startEdit(m)} className="btn-secondary h-9 px-3 text-xs">
                        <Pencil className="mr-1 size-3.5" /> Edit
                      </button>
                      {m.transcript && !m.summary && (
                        <LoadingButton
                          variant="secondary"
                          className="h-9 px-3 text-xs"
                          loading={summarizing === m.id}
                          loadingText="Summarizing..."
                          onClick={() => handleSummarize(m.id)}
                        >
                          <Sparkles className="mr-1 size-3.5" /> AI Summary
                        </LoadingButton>
                      )}
                      <LoadingButton
                        variant="secondary"
                        className="h-9 border-red-500/20 bg-red-500/10 px-3 text-xs text-red-400 hover:bg-red-500/20"
                        loading={deletingId === m.id}
                        loadingText="Deleting..."
                        onClick={() => handleDelete(m.id, m.title)}
                      >
                        <Trash2 className="mr-1 size-3.5" /> Delete
                      </LoadingButton>
                    </div>
                  </div>

                  {expanded && (
                    <div className="border-t border-slate-800 px-5 pb-5 pt-4 space-y-4">
                      {m.transcript && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Transcript</p>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{m.transcript}</p>
                        </div>
                      )}
                      {m.summary && (
                        <div className="rounded-xl border border-[#d26e41]/20 bg-[#d26e41]/5 p-4">
                          <p className="text-xs font-semibold uppercase text-[#d26e41]">AI Summary</p>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{m.summary}</p>
                        </div>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
