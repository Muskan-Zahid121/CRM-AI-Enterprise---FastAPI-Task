import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { getAuthToken, getStoredUser } from '@/api/client';
import AppLayout from '@/components/layout/AppLayout';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import ContactsPage from '@/pages/ContactsPage';
import EmailPage from '@/pages/EmailPage';
import WorkflowsPage from '@/pages/WorkflowsPage';
import SettingsPage from '@/pages/SettingsPage';
import DashboardPage from '@/pages/DashboardPage';
import CustomersPage from '@/pages/CustomersPage';
import LeadsPage from '@/pages/LeadsPage';
import DealsPage from '@/pages/DealsPage';
import TasksPage from '@/pages/TasksPage';
import MeetingsPage from '@/pages/MeetingsPage';
import KnowledgePage from '@/pages/KnowledgePage';
import ChatPage from '@/pages/ChatPage';
import { Toaster } from '@/components/ui/toaster';
import { ConfirmProvider } from '@/components/ui/confirm-modal';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return getAuthToken() ? children : <Navigate to="/login" replace />;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  return getAuthToken() ? <Navigate to="/dashboard" replace /> : children;
}

function AppRoutes() {
  const navigate = useNavigate();
  const [, setAuthVersion] = useState(0);
  const refreshAuth = () => setAuthVersion((v) => v + 1);

  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage onSuccess={refreshAuth} onGoSignup={() => navigate('/signup')} />
          </PublicRoute>
        }
      />
      <Route
        path="/signup"
        element={
          <PublicRoute>
            <SignupPage onSuccess={refreshAuth} onGoLogin={() => navigate('/login')} />
          </PublicRoute>
        }
      />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout onLogout={refreshAuth} />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/contacts" element={<ContactsPage />} />
        <Route path="/leads" element={<LeadsPage />} />
        <Route path="/deals" element={<DealsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/meetings" element={<MeetingsPage />} />
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/email" element={<EmailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  if (getAuthToken() && !getStoredUser()) {
    localStorage.removeItem('token');
  }

  return (
    <BrowserRouter>
      <ConfirmProvider>
        <AppRoutes />
        <Toaster />
      </ConfirmProvider>
    </BrowserRouter>
  );
}
