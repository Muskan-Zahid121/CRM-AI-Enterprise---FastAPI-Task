import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  Bot,
  Briefcase,
  BookOpen,
  Loader2,
  Mail,
  MessageSquare,
  Plus,
  Sparkles,
  Trash2,
  Zap,
} from 'lucide-react';
import { chatStream } from '@/api/chat';
import { platformApi, type ChatMessage, type ChatSession } from '@/api/platform';
import { LoadingButton } from '@/components/ui/loading-button';
import { useConfirm } from '@/components/ui/confirm-modal';
import { cn } from '@/lib/utils';

const SUGGESTIONS = [
  'Add a customer for Sarah Johnson. Company: Digital Marketing Hub. Email: sarah@dmhub.com Phone: +1-555-987-6543',
  'Who is my latest customer?',
  'Show my CRM pipeline overview',
  'What does our pricing document say?',
  'Tell me about the uploaded policy document',
];

const AGENT_COLORS: Record<string, string> = {
  crm: 'text-orange-400 bg-orange-500/10 ring-orange-500/20',
  knowledge: 'text-violet-400 bg-violet-500/10 ring-violet-500/20',
  meeting: 'text-sky-400 bg-sky-500/10 ring-sky-500/20',
  email: 'text-emerald-400 bg-emerald-500/10 ring-emerald-500/20',
  task: 'text-amber-400 bg-amber-500/10 ring-amber-500/20',
  analytics: 'text-pink-400 bg-pink-500/10 ring-pink-500/20',
  router: 'text-slate-400 bg-slate-500/10 ring-slate-500/20',
};

function renderFormatted(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i} className="font-semibold text-slate-100">{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

function AgentBadge({ agent }: { agent?: string | null }) {
  if (!agent) return null;
  const style = AGENT_COLORS[agent] ?? AGENT_COLORS.router;
  const icons: Record<string, typeof Bot> = {
    crm: Briefcase,
    knowledge: BookOpen,
    email: Mail,
    task: Zap,
    meeting: MessageSquare,
    analytics: Sparkles,
    router: Bot,
  };
  const Icon = icons[agent] ?? Bot;
  return (
    <span className={cn('mb-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1', style)}>
      <Icon className="size-3" />
      {agent} agent
    </span>
  );
}

export default function ChatPage() {
  const confirm = useConfirm();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [creatingChat, setCreatingChat] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const [loadingSessionId, setLoadingSessionId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function loadSessions() {
    const res = await platformApi.listChatSessions();
    setSessions(res.sessions);
  }

  async function loadSessionMessages(sessionId: number) {
    const res = await platformApi.getSessionMessages(sessionId);
    setMessages(res.messages);
  }

  useEffect(() => { loadSessions().catch(console.error); }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText, loading]);

  async function startNewChat() {
    setCreatingChat(true);
    try {
      const res = await platformApi.createChatSession();
      const session = res.session;
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
      setInput('');
    } finally {
      setCreatingChat(false);
    }
  }

  async function selectSession(sessionId: number) {
    setLoadingSessionId(sessionId);
    setActiveSessionId(sessionId);
    try {
      await loadSessionMessages(sessionId);
    } finally {
      setLoadingSessionId(null);
    }
  }

  async function deleteSession(sessionId: number) {
    const session = sessions.find((s) => s.id === sessionId);
    const ok = await confirm({
      title: 'Delete chat',
      message: `Delete "${session?.title ?? 'this conversation'}"? All messages will be permanently removed.`,
      confirmText: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingSessionId(sessionId);
    try {
      await platformApi.deleteChatSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
      }
      await loadSessions();
    } finally {
      setDeletingSessionId(null);
    }
  }

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      const res = await platformApi.createChatSession();
      sessionId = res.session.id;
      setSessions((prev) => [res.session, ...prev]);
      setActiveSessionId(sessionId);
    }

    setLoading(true);
    setStreamingText('');
    setMessages((prev) => [...prev, { message: text, response: '' }]);

    try {
      let accumulated = '';
      await chatStream(
        text,
        sessionId,
        (chunk) => {
          accumulated += chunk;
          setStreamingText(accumulated);
        },
        (meta) => {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { message: text, response: accumulated, agent: meta.agent };
            return next;
          });
          setStreamingText('');
          if (meta.session_title) {
            setSessions((prev) =>
              prev.map((s) => (s.id === meta.session_id ? { ...s, title: meta.session_title! } : s)),
            );
          }
          loadSessions().catch(console.error);
        },
      );
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          message: text,
          response: err instanceof Error ? err.message : 'Something went wrong.',
        };
        return next;
      });
      setStreamingText('');
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput('');
    await sendMessage(text);
  }

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row lg:gap-4">
      {/* Sessions sidebar */}
      <aside className="flex w-full shrink-0 flex-col rounded-2xl border border-slate-800 bg-slate-900/60 lg:w-64">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Chats</p>
          <button
            type="button"
            onClick={startNewChat}
            disabled={creatingChat}
            className="inline-flex items-center gap-1 rounded-lg bg-[#d26e41]/15 px-2 py-1 text-xs font-medium text-[#d26e41] hover:bg-[#d26e41]/25 disabled:opacity-50"
          >
            {creatingChat ? <Loader2 className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />}
            {creatingChat ? 'Creating...' : 'New'}
          </button>
        </div>
        <div className="max-h-32 overflow-y-auto brand-scrollbar p-2 lg:max-h-none lg:flex-1">
          {sessions.length === 0 ? (
            <p className="px-2 py-4 text-xs text-slate-500">No chats yet. Start a new conversation.</p>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className={cn(
                  'group mb-1 flex items-center gap-1 rounded-lg transition-colors',
                  activeSessionId === s.id
                    ? 'bg-[#d26e41]/15 ring-1 ring-[#d26e41]/20'
                    : 'hover:bg-slate-800/80',
                )}
              >
                <button
                  type="button"
                  onClick={() => selectSession(s.id)}
                  disabled={loadingSessionId === s.id || deletingSessionId === s.id}
                  className={cn(
                    'min-w-0 flex-1 rounded-lg px-3 py-2.5 text-left text-xs transition-colors disabled:opacity-60',
                    activeSessionId === s.id ? 'text-[#d26e41]' : 'text-slate-400 group-hover:text-slate-200',
                  )}
                >
                  <p className="flex items-center gap-1.5 truncate font-medium">
                    {loadingSessionId === s.id && <Loader2 className="size-3 shrink-0 animate-spin" />}
                    {s.title}
                  </p>
                  {s.updated_at && (
                    <p className="mt-0.5 truncate text-[10px] opacity-60">
                      {new Date(s.updated_at).toLocaleDateString()}
                    </p>
                  )}
                </button>
                <button
                  type="button"
                  title="Delete chat"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(s.id);
                  }}
                  disabled={deletingSessionId === s.id}
                  className={cn(
                    'mr-1.5 shrink-0 rounded-md p-1.5 text-slate-500 opacity-0 transition-all',
                    'hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100',
                    'focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40',
                    deletingSessionId === s.id && 'opacity-100',
                  )}
                >
                  {deletingSessionId === s.id ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="size-3.5" />
                  )}
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main chat */}
      <div className="mt-4 flex min-w-0 flex-1 flex-col lg:mt-0">
        <div className="mb-4">
          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold text-slate-100">
              {activeSession?.title ?? 'AI Sales Assistant'}
            </h1>
            <p className="mt-0.5 text-sm text-slate-500">
              {activeSessionId
                ? 'Messages stay in this chat session'
                : 'Start a new chat or select one from the sidebar'}
            </p>
          </div>
        </div>

        <div className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40">
          <div className="flex-1 space-y-5 overflow-y-auto p-5 brand-scrollbar">
            {!activeSessionId && messages.length === 0 && !loading && (
              <div className="flex flex-col items-center py-12 text-center">
                <div className="rounded-2xl bg-[#d26e41]/10 p-4 ring-1 ring-[#d26e41]/20">
                  <Bot className="size-10 text-[#d26e41]" />
                </div>
                <h2 className="mt-5 text-lg font-medium text-slate-200">Start a conversation</h2>
                <p className="mt-2 max-w-md text-sm text-slate-500">
                  Click <strong className="text-slate-400">New</strong> to create a chat session, then send messages — they all stay in that session.
                </p>
                <LoadingButton loading={creatingChat} loadingText="Creating..." onClick={startNewChat} className="mt-6">
                  <Plus className="mr-2 size-4" /> New chat
                </LoadingButton>
              </div>
            )}

            {activeSessionId && messages.length === 0 && !loading && (
              <div className="flex flex-col items-center py-8 text-center">
                <p className="text-sm text-slate-500">This session is empty. Send a message below.</p>
                <div className="mt-4 grid w-full max-w-lg gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => sendMessage(s)}
                      className="rounded-xl border border-slate-700/80 bg-slate-800/50 px-4 py-2.5 text-left text-xs text-slate-400 transition-colors hover:border-[#d26e41]/30 hover:text-slate-200"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => {
              const isLast = i === messages.length - 1;
              const displayResponse = isLast && loading && streamingText ? streamingText : m.response;
              const showTyping = isLast && loading && !streamingText;

              return (
                <div key={m.id ?? i} className="space-y-3">
                  <div className="ml-auto max-w-[85%]">
                    <div className="rounded-2xl rounded-br-md bg-[#d26e41] px-4 py-3 text-sm text-white shadow-lg shadow-[#d26e41]/10">
                      {m.message}
                    </div>
                  </div>
                  {(displayResponse || showTyping) && (
                    <div className="max-w-[90%]">
                      <div className="rounded-2xl rounded-bl-md border border-slate-700/80 bg-slate-800/80 px-4 py-3 text-sm leading-relaxed text-slate-300 shadow-sm">
                        <AgentBadge agent={m.agent} />
                        {showTyping ? (
                          <span className="inline-flex gap-1">
                            <span className="size-2 animate-bounce rounded-full bg-[#d26e41]" />
                            <span className="size-2 animate-bounce rounded-full bg-[#d26e41]" style={{ animationDelay: '150ms' }} />
                            <span className="size-2 animate-bounce rounded-full bg-[#d26e41]" style={{ animationDelay: '300ms' }} />
                          </span>
                        ) : (
                          <div className="whitespace-pre-wrap">{renderFormatted(displayResponse ?? '')}</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSend} className="border-t border-slate-800 p-4">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={activeSessionId ? 'Message in this session...' : 'Create or select a chat first...'}
                className="input-dark flex-1"
                disabled={loading}
              />
              <LoadingButton type="submit" loading={loading} loadingText="Working..." disabled={!input.trim()} className="min-w-[100px]">
                Send
              </LoadingButton>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
