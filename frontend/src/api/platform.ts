import { api, apiUpload } from './client';

export interface Customer {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  status: string;
}

export interface Contact {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  customer_id?: number | null;
  is_primary: boolean;
}

export interface Lead {
  id: number;
  name: string;
  email?: string | null;
  company?: string | null;
  stage: string;
  score: number;
}

export interface Deal {
  id: number;
  title: string;
  value: number;
  stage: string;
  customer_id?: number | null;
  probability: number;
}

export interface Task {
  id: number;
  title: string;
  status: string;
  priority: string;
  due_date?: string | null;
}

export interface Meeting {
  id: number;
  title: string;
  summary?: string | null;
  transcript?: string | null;
  customer_id?: number | null;
  created_at?: string | null;
}

export interface Note {
  id: number;
  content: string;
  customer_id?: number | null;
  deal_id?: number | null;
}

export interface WorkflowStep {
  action: string;
  title?: string;
  subject?: string;
  prompt?: string;
  priority?: string;
  _meta?: boolean;
  template?: string;
  trigger?: string;
}

export interface Workflow {
  id: number;
  name: string;
  description?: string;
  status: string;
  steps?: WorkflowStep[];
  step_count?: number;
}

export interface WorkflowTemplate {
  key: string;
  name: string;
  description: string;
  trigger: string;
  steps: WorkflowStep[];
}

export interface WorkflowExecutionHistory {
  id: number;
  workflow_id: number;
  workflow_name: string;
  status: string;
  summary?: string;
  created_at?: string;
}

export interface DocumentItem {
  id: number;
  title: string;
  indexed: boolean;
  chunk_count: number;
}

export interface RagResult {
  id?: number;
  document_id: number;
  chunk_index: number;
  content: string;
  score?: number;
}

export interface EmailRecord {
  id: number;
  subject: string;
  body?: string;
  sent?: boolean;
}

export interface Notification {
  id: number;
  title: string;
  body: string;
  read: boolean;
}

export interface ActivityItem {
  id: number;
  type: string;
  description: string;
}

export const platformApi = {
  // Dashboard
  dashboard: () => api.get<DashboardOverview>('/api/dashboard'),
  dashboardStats: () => api.get<{ success: boolean; stats: DashboardOverview & { rag?: Record<string, unknown> } }>('/api/dashboard/stats'),
  dashboardRecent: () => api.get('/api/dashboard/recent'),
  dashboardActivity: () => api.get<{ success: boolean; activity: ActivityItem[] }>('/api/dashboard/activity'),

  // Customers
  listCustomers: (search?: string) =>
    api.get<{ success: boolean; customers: Customer[] }>(`/api/customers${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  createCustomer: (body: Partial<Customer> & { name: string }) =>
    api.post<{ success: boolean; customer: Customer }>('/api/customers', body),
  deleteCustomer: (id: number) => api.delete(`/api/customers/${id}`),

  // Contacts
  listContacts: () => api.get<{ success: boolean; contacts: Contact[] }>('/api/contacts'),
  createContact: (body: Partial<Contact> & { name: string }) => api.post('/api/contacts', body),
  deleteContact: (id: number) => api.delete(`/api/contacts/${id}`),

  // Notes
  listNotes: () => api.get<{ success: boolean; notes: Note[] }>('/api/notes'),
  createNote: (body: { content: string; customer_id?: number; deal_id?: number }) => api.post('/api/notes', body),
  deleteNote: (id: number) => api.delete(`/api/notes/${id}`),

  // Leads
  listLeads: () => api.get<{ success: boolean; leads: Lead[] }>('/api/leads'),
  createLead: (body: Partial<Lead> & { name: string }) => api.post('/api/leads', body),
  convertLead: (leadId: number) => api.put(`/api/leads/${leadId}/convert`),
  leadsPipeline: () => api.get<{ success: boolean; pipeline: Record<string, number> }>('/api/leads/pipeline'),
  deleteLead: (id: number) => api.delete(`/api/leads/${id}`),

  // Deals
  listDeals: (stage?: string) =>
    api.get<{ success: boolean; deals: Deal[] }>(`/api/deals${stage ? `?stage=${stage}` : ''}`),
  createDeal: (body: Partial<Deal> & { title: string }) => api.post('/api/deals', body),
  dealsPipeline: () => api.get<{ success: boolean; pipeline: Record<string, number> }>('/api/deals/pipeline'),
  dealsForecast: () => api.get<{ success: boolean; forecast: number }>('/api/deals/forecast'),
  changeDealStage: (dealId: number, stage: string) =>
    api.put(`/api/deals/change-stage?deal_id=${dealId}&stage=${stage}`),
  deleteDeal: (id: number) => api.delete(`/api/deals/${id}`),

  // Tasks
  listTasks: (status?: string) =>
    api.get<{ success: boolean; tasks: Task[] }>(`/api/tasks${status ? `?status=${status}` : ''}`),
  createTask: (body: Partial<Task> & { title: string }) => api.post('/api/tasks', body),
  completeTask: (taskId: number) => api.put(`/api/tasks/${taskId}/complete`),
  pendingTasks: () => api.get('/api/tasks/pending'),
  deleteTask: (id: number) => api.delete(`/api/tasks/${id}`),

  // Meetings
  listMeetings: () => api.get<{ success: boolean; meetings: Meeting[] }>('/api/meetings'),
  getMeeting: (id: number) => api.get<{ success: boolean; meeting: Meeting }>(`/api/meetings/${id}`),
  createMeeting: (body: Partial<Meeting> & { title: string }) => api.post('/api/meetings', body),
  updateMeeting: (id: number, body: Partial<Meeting> & { title: string }) => api.put(`/api/meetings/${id}`, body),
  summarizeMeeting: (meetingId: number) =>
    api.get<{ success: boolean; summary: string }>(`/api/transcripts/summary?meeting_id=${meetingId}`),
  deleteMeeting: (id: number) => api.delete(`/api/meetings/${id}`),

  // Workflows
  listWorkflows: () => api.get<{ success: boolean; workflows: Workflow[] }>('/api/workflows'),
  listWorkflowTemplates: () =>
    api.get<{ success: boolean; templates: WorkflowTemplate[] }>('/api/workflows/templates'),
  createWorkflow: (body: { template: string; name?: string; description?: string }) =>
    api.post<{ success: boolean; workflow: Workflow }>('/api/workflows', body),
  executeWorkflow: (workflowId: number, context?: Record<string, string>) =>
    api.post<{ success: boolean; execution: { id: number; status: string; result?: { summary?: string } } }>(
      '/api/workflows/execute',
      { workflow_id: workflowId, context: context ?? {} },
    ),
  deleteWorkflow: (id: number) => api.delete(`/api/workflows/${id}`),
  workflowHistory: () =>
    api.get<{ success: boolean; history: WorkflowExecutionHistory[] }>('/api/workflows/history'),

  // Knowledge & RAG
  listDocuments: () => api.get<{ success: boolean; documents: DocumentItem[] }>('/api/documents'),
  uploadKnowledge: (body: { title: string; content: string; tags?: string[] }) =>
    api.post<{ success: boolean; document: { id: number; title: string; chunks: number } }>(
      '/api/knowledge/upload',
      { ...body, file_type: 'text', tags: body.tags ?? [] },
    ),
  uploadKnowledgeFile: (file: File, title?: string) => {
    const form = new FormData();
    form.append('file', file);
    if (title?.trim()) form.append('title', title.trim());
    return apiUpload<{ success: boolean; document: { id: number; title: string; chunks: number; file_type: string; characters: number } }>(
      '/api/knowledge/upload-file',
      form,
    );
  },
  searchKnowledge: (q: string) =>
    api.post<{ success: boolean; results: RagResult[] }>(`/api/knowledge/search?q=${encodeURIComponent(q)}`),
  ragQuery: (query: string) => api.post<{ success: boolean; answer: string; citations: RagResult[] }>('/api/rag/query', { query }),
  ragStats: () => api.get<{ success: boolean; stats: { total_chunks: number; indexed_documents: number } }>('/api/rag/statistics'),
  deleteDocument: (documentId: number) =>
    api.delete(`/api/knowledge/?document_id=${documentId}`),

  // Chat & Agents — session-based
  createChatSession: () =>
    api.post<{ success: boolean; session: ChatSession }>('/api/chat/sessions'),
  listChatSessions: () =>
    api.get<{ success: boolean; sessions: ChatSession[] }>('/api/chat/sessions'),
  getSessionMessages: (sessionId: number) =>
    api.get<{ success: boolean; messages: ChatMessage[] }>(`/api/chat/sessions/${sessionId}/messages`),
  deleteChatSession: (sessionId: number) => api.delete(`/api/chat/sessions/${sessionId}`),
  chat: (message: string, sessionId: number) =>
    api.post<{ success: boolean; response: string; agent: string; citations: RagResult[]; session_id: number }>(
      '/api/chat',
      { message, session_id: sessionId },
    ),

  // Email
  generateEmail: (subject: string, prompt: string, customerId?: number) =>
    api.post<{ success: boolean; email: EmailRecord }>('/api/email/generate', { subject, prompt, customer_id: customerId }),
  emailHistory: () => api.get<{ success: boolean; emails: EmailRecord[] }>('/api/email/history'),
  sendEmail: (emailId: number) => api.post(`/api/email/send?email_id=${emailId}`),

  // Search
  globalSearch: (query: string) =>
    api.post<{ success: boolean; customers: { id: number; name: string }[]; documents: RagResult[] }>(
      '/api/search/global',
      { query },
    ),

  // Notifications
  listNotifications: () => api.get<{ success: boolean; notifications: Notification[] }>('/api/notifications'),
  markNotificationRead: (id: number) => api.put(`/api/notifications/${id}`),
  deleteNotification: (id: number) => api.delete(`/api/notifications/${id}`),

  // Settings
  getSettings: () => api.get<{ success: boolean; settings: Record<string, unknown> }>('/api/settings'),
  updateSettings: (settings: Record<string, unknown>) => api.put('/api/settings', settings),
};

export interface DashboardOverview {
  success?: boolean;
  customers: number;
  deals: number;
  open_deals: number;
  pending_tasks: number;
  meetings: number;
  documents: number;
  pipeline_value: number;
  recent_deals: { id: number; title: string; stage: string; value: number }[];
  recent_tasks: { id: number; title: string; status: string; priority: string }[];
}

export interface ChatSession {
  id: number;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  id?: number;
  message: string;
  response?: string | null;
  agent?: string | null;
}
