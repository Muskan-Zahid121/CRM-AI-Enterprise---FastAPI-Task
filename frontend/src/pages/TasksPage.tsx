import { useEffect, useState, type FormEvent } from 'react';
import { CheckCircle2, Circle, ListTodo } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingButton } from '@/components/ui/loading-button';
import { StatusBadge } from '@/components/ui/status-badge';
import { platformApi, type Task } from '@/api/platform';

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState('medium');
  const [creating, setCreating] = useState(false);
  const [completingId, setCompletingId] = useState<number | null>(null);

  async function load() {
    const res = await platformApi.listTasks();
    setTasks(res.tasks);
  }

  useEffect(() => { load().catch(console.error); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await platformApi.createTask({ title, priority, status: 'pending' });
      setTitle('');
      await load();
    } finally {
      setCreating(false);
    }
  }

  async function handleComplete(id: number) {
    setCompletingId(id);
    try {
      await platformApi.completeTask(id);
      await load();
    } finally {
      setCompletingId(null);
    }
  }

  const pendingCount = tasks.filter((t) => t.status !== 'completed').length;
  const completedCount = tasks.filter((t) => t.status === 'completed').length;

  return (
    <div>
      <PageHeader title="Tasks" subtitle="Track follow-ups and sales actions" />

      <form onSubmit={handleCreate} className="card-surface mb-6 grid gap-3 p-5 md:grid-cols-4">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Task title" required className="input-dark md:col-span-2" />
        <select value={priority} onChange={(e) => setPriority(e.target.value)} className="input-dark">
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <LoadingButton type="submit" loading={creating} loadingText="Adding...">Add Task</LoadingButton>
      </form>

      {tasks.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-3 text-sm text-slate-400">
          <span className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1">
            <span className="font-medium text-slate-200">{pendingCount}</span> pending
          </span>
          <span className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1">
            <span className="font-medium text-slate-200">{completedCount}</span> completed
          </span>
        </div>
      )}

      {tasks.length === 0 ? (
        <EmptyState icon={ListTodo} title="No tasks yet" description="Add a task above or let a workflow create follow-ups for you." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tasks.map((t) => {
            const isCompleted = t.status === 'completed';
            return (
              <article
                key={t.id}
                className={`card-surface flex h-full flex-col p-5 transition-all ${
                  isCompleted
                    ? 'border-slate-800/80 opacity-75'
                    : 'hover:border-[#d26e41]/25 hover:shadow-md hover:shadow-black/20'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 shrink-0 ${isCompleted ? 'text-emerald-400/70' : 'text-slate-500'}`}>
                    {isCompleted ? <CheckCircle2 className="size-5" /> : <Circle className="size-5" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3
                      className={`line-clamp-2 font-medium leading-snug ${
                        isCompleted ? 'text-slate-500 line-through' : 'text-slate-100'
                      }`}
                    >
                      {t.title}
                    </h3>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <StatusBadge status={t.priority} className="dark-badge" />
                      <StatusBadge status={t.status} className="dark-badge" />
                    </div>
                  </div>
                </div>

                {!isCompleted && (
                  <div className="mt-4 border-t border-slate-800 pt-4">
                    <LoadingButton
                      variant="secondary"
                      className="h-9 w-full text-xs"
                      loading={completingId === t.id}
                      loadingText="Completing..."
                      onClick={() => handleComplete(t.id)}
                    >
                      <CheckCircle2 className="mr-1.5 size-3.5" />
                      Complete Task
                    </LoadingButton>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
