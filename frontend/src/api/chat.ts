import { getAuthToken } from './client';
import { API_BASE_URL } from '@/lib/config';
import { toast } from '@/lib/toast';
import type { RagResult } from './platform';

export interface ChatStreamDone {
  session_id: number;
  session_title?: string;
  agent: string;
  citations: RagResult[];
  chat_id: number;
  actions: string[];
}

export async function chatStream(
  message: string,
  sessionId: number,
  onChunk: (chunk: string) => void,
  onDone: (meta: ChatStreamDone) => void,
): Promise<void> {
  const token = getAuthToken();
  const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    const text = await res.text();
    let msg = text || 'Chat stream failed';
    try {
      const parsed = JSON.parse(text) as { detail?: string; message?: string };
      msg = parsed.detail ?? parsed.message ?? msg;
    } catch {
      /* plain text error */
    }
    toast.error(msg);
    throw new Error(msg);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response stream');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = JSON.parse(line.slice(6)) as {
        chunk?: string;
        done?: boolean;
        session_id?: number;
        session_title?: string;
        agent?: string;
        citations?: RagResult[];
        chat_id?: number;
        actions?: string[];
      };
      if (payload.chunk) onChunk(payload.chunk);
      if (payload.done) {
        onDone({
          session_id: payload.session_id!,
          session_title: payload.session_title,
          agent: payload.agent ?? 'router',
          citations: payload.citations ?? [],
          chat_id: payload.chat_id!,
          actions: payload.actions ?? [],
        });
      }
    }
  }
}
