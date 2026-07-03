import { useEffect, useState, type FormEvent } from 'react';
import { Mail, Send, Sparkles } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { AlertBanner } from '@/components/ui/alert-banner';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingButton } from '@/components/ui/loading-button';
import { StatusBadge } from '@/components/ui/status-badge';
import { platformApi, type EmailRecord } from '@/api/platform';

export default function EmailPage() {
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [subject, setSubject] = useState('');
  const [prompt, setPrompt] = useState('');
  const [generated, setGenerated] = useState<EmailRecord | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingId, setSendingId] = useState<number | null>(null);

  async function load() {
    const res = await platformApi.emailHistory();
    setEmails(res.emails);
  }

  useEffect(() => { load().catch(console.error); }, []);

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await platformApi.generateEmail(subject, prompt);
      setGenerated(res.email);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(id: number) {
    setSendingId(id);
    try {
      await platformApi.sendEmail(id);
      await load();
    } finally {
      setSendingId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Email Assistant" subtitle="AI-generated follow-ups and outreach drafts" />
      <AlertBanner message={error} onDismiss={() => setError('')} />

      <form onSubmit={handleGenerate} className="card-surface mb-6 space-y-4 p-6">
        <div className="flex items-center gap-2 text-[#d26e41]">
          <Sparkles className="size-4" />
          <span className="text-sm font-medium">Generate with AI</span>
        </div>
        <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Email subject" required className="input-dark w-full" />
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Describe the email context, tone, and key points..." rows={4} required className="input-dark w-full min-h-[100px] py-3" />
        <LoadingButton type="submit" loading={loading} loadingText="Generating..." className="w-full sm:w-auto">
          Generate Email
        </LoadingButton>
      </form>

      {generated?.body && (
        <div className="card-surface mb-6 border-[#d26e41]/20 p-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-[#d26e41]">Draft Preview</p>
          <p className="mt-2 font-medium text-slate-900">{generated.subject}</p>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{generated.body}</p>
          {generated.id && (
            <LoadingButton
              loading={sendingId === generated.id}
              loadingText="Sending..."
              className="mt-4"
              onClick={() => handleSend(generated.id!)}
            >
              <Send className="mr-2 size-4" /> Mark as Sent
            </LoadingButton>
          )}
        </div>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">History</h2>
        {emails.length === 0 ? (
          <EmptyState icon={Mail} title="No emails yet" description="Generated emails will appear here." />
        ) : (
          <div className="space-y-2">
            {emails.map((e) => (
              <div key={e.id} className="card-surface flex items-center justify-between gap-4 p-4">
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-900">{e.subject}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <StatusBadge status={e.sent ? 'completed' : 'pending'} />
                  {!e.sent && (
                    <LoadingButton
                      variant="secondary"
                      className="h-9 px-3 text-xs"
                      loading={sendingId === e.id}
                      loadingText="Sending..."
                      onClick={() => handleSend(e.id)}
                    >
                      Send
                    </LoadingButton>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
