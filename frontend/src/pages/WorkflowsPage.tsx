import { useEffect, useState, type FormEvent } from 'react';
import { GitBranch, Play, Plus, Trash2, Zap } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { useConfirm } from '@/components/ui/confirm-modal';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingButton } from '@/components/ui/loading-button';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  platformApi,
  type Workflow,
  type WorkflowExecutionHistory,
  type WorkflowTemplate,
} from '@/api/platform';
import { toast } from '@/lib/toast';

function visibleSteps(steps: Workflow['steps']) {
  return (steps ?? []).filter((s) => !s._meta);
}

function formatTrigger(trigger?: string) {
  if (!trigger) return 'Manual only';
  return trigger
    .split('_or_')
    .map((t) => t.replace(/_/g, ' '))
    .join(' · ');
}

function formatAction(action: string) {
  return action.replace(/_/g, ' ');
}

export default function WorkflowsPage() {
  const confirm = useConfirm();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [history, setHistory] = useState<WorkflowExecutionHistory[]>([]);
  const [name, setName] = useState('');
  const [templateKey, setTemplateKey] = useState('lead_follow_up');
  const [running, setRunning] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  const selectedTemplate = templates.find((t) => t.key === templateKey);

  async function load() {
    const [w, t, h] = await Promise.all([
      platformApi.listWorkflows(),
      platformApi.listWorkflowTemplates(),
      platformApi.workflowHistory(),
    ]);
    setWorkflows(w.workflows);
    setTemplates(t.templates);
    setHistory(h.history ?? []);
    if (t.templates.length && !t.templates.some((x) => x.key === templateKey)) {
      setTemplateKey(t.templates[0].key);
    }
  }

  useEffect(() => {
    load().catch((e) => toast.error(e instanceof Error ? e.message : 'Failed to load workflows'));
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await platformApi.createWorkflow({
        template: templateKey,
        name: name.trim() || undefined,
      });
      setName('');
      toast.success('Workflow created');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  }

  async function handleExecute(id: number) {
    setRunning(id);
    try {
      const res = await platformApi.executeWorkflow(id);
      const summary = res.execution.result?.summary;
      toast.success(res.execution.status === 'completed' ? 'Workflow completed' : 'Workflow finished with errors');
      if (summary) toast.info(summary.replace(/\n/g, ' · '));
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Execution failed');
    } finally {
      setRunning(null);
    }
  }

  async function handleDelete(id: number, workflowName: string) {
    const ok = await confirm({
      title: 'Delete workflow',
      message: `Delete "${workflowName}"? Execution history for this workflow will also be removed.`,
      confirmText: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    setDeleting(id);
    try {
      await platformApi.deleteWorkflow(id);
      toast.success('Workflow deleted');
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Workflows"
        subtitle="When something happens, run a chain of actions automatically"
      />
      <form onSubmit={handleCreate} className="card-surface mb-6 space-y-4 p-5">
        <h2 className="text-sm font-semibold text-slate-200">New workflow from template</h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-500">
              Template
            </label>
            <select
              value={templateKey}
              onChange={(e) => setTemplateKey(e.target.value)}
              className="input-dark w-full"
            >
              {templates.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-500">
              Custom name (optional)
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={selectedTemplate?.name ?? 'Workflow name'}
              className="input-dark w-full"
            />
          </div>
        </div>

        {selectedTemplate && (
          <div className="rounded-xl border border-[#d26e41]/20 bg-[#d26e41]/5 p-4">
            <div className="flex items-start gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[#d26e41]/15 text-[#d26e41]">
                <Zap className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-200">{selectedTemplate.description}</p>
                <p className="mt-2 text-xs uppercase tracking-wider text-[#d26e41]/80">
                  Trigger: {formatTrigger(selectedTemplate.trigger)}
                </p>
                <ol className="mt-3 space-y-2">
                  {selectedTemplate.steps.map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-400">
                        {i + 1}
                      </span>
                      <span>
                        <span className="font-medium capitalize text-slate-100">{formatAction(step.action)}</span>
                        {step.title && <span className="text-slate-400"> — {step.title}</span>}
                        {step.subject && <span className="text-slate-400"> — {step.subject}</span>}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        )}

        <LoadingButton type="submit" loading={creating} loadingText="Creating..." className="sm:w-auto">
          <Plus className="mr-2 size-4" /> Create Workflow
        </LoadingButton>
      </form>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Your workflows</h2>
          {workflows.length === 0 ? (
            <EmptyState
              icon={GitBranch}
              title="No workflows yet"
              description="Pick a template above — each workflow chains tasks, emails, and notifications."
            />
          ) : (
            <div className="space-y-3">
              {workflows.map((w) => {
                const steps = visibleSteps(w.steps);
                const trigger = w.steps?.find((s) => s._meta)?.trigger;
                const isLegacy = steps.length === 0;

                return (
                  <article key={w.id} className="card-surface overflow-hidden">
                    <div className="flex flex-wrap items-start justify-between gap-3 p-5">
                      <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-slate-100">{w.name}</h3>
                        {w.description && <p className="mt-1 text-sm text-slate-400">{w.description}</p>}
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <StatusBadge status={w.status} className="dark-badge" />
                          <span className="text-xs text-slate-500">{steps.length} steps</span>
                          <span className="text-xs text-slate-600">·</span>
                          <span className="text-xs text-slate-500">{formatTrigger(trigger)}</span>
                        </div>
                        {isLegacy && (
                          <p className="mt-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs text-slate-400">
                            This workflow has no steps (created before templates). Delete it and create a new one from a template.
                          </p>
                        )}
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <LoadingButton
                          loading={running === w.id}
                          loadingText="Running..."
                          className="h-9 px-3 text-xs"
                          disabled={isLegacy}
                          onClick={() => handleExecute(w.id)}
                        >
                          <Play className="mr-1.5 size-3.5" />
                          Execute
                        </LoadingButton>
                        <LoadingButton
                          variant="secondary"
                          loading={deleting === w.id}
                          loadingText="Deleting..."
                          className="h-9 border-red-500/20 bg-red-500/10 px-3 text-xs text-red-400 hover:bg-red-500/20"
                          onClick={() => handleDelete(w.id, w.name)}
                          aria-label="Delete workflow"
                        >
                          <Trash2 className="size-4" />
                          Delete
                        </LoadingButton>
                      </div>
                    </div>

                    {steps.length > 0 && (
                      <div className="border-t border-slate-800 px-5 pb-5 pt-4">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Steps</p>
                        <ol className="mt-2 space-y-1.5">
                          {steps.map((step, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                              <span className="text-slate-600">{i + 1}.</span>
                              <span className="capitalize text-slate-300">{formatAction(step.action)}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">Execution history</h2>
          <div className="card-surface divide-y divide-slate-800">
            {history.length === 0 ? (
              <p className="p-5 text-sm text-slate-500">
                No runs yet. Click Execute on a workflow, or create a lead to auto-trigger Lead Follow-up.
              </p>
            ) : (
              history.map((h) => (
                <div key={h.id} className="px-5 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-medium text-slate-100">{h.workflow_name}</p>
                      {h.created_at && (
                        <p className="mt-0.5 text-xs text-slate-500">
                          {new Date(h.created_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <StatusBadge status={h.status} className="dark-badge shrink-0" />
                  </div>
                  {h.summary && (
                    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-800/50 px-3 py-2">
                      <p className="whitespace-pre-line text-xs leading-relaxed text-slate-400">{h.summary}</p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
