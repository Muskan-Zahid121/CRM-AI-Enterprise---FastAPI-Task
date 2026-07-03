import { api, setAuthSession } from './client';
import { dispatchAuthUserUpdated } from '@/lib/auth-storage';

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  role?: string;
}

interface AuthResponse {
  success: boolean;
  message?: string;
  token?: string;
  user?: AuthUser;
}

export const authApi = {
  register: async (name: string, email: string, password: string) => {
    const res = await api.post<AuthResponse>('/api/auth/register', { name, email, password });
    if (res.token && res.user) {
      setAuthSession(res.token, res.user);
      dispatchAuthUserUpdated();
    }
    return res;
  },

  login: async (email: string, password: string) => {
    const res = await api.post<AuthResponse>('/api/auth/login', { email, password });
    if (res.token && res.user) {
      setAuthSession(res.token, res.user);
      dispatchAuthUserUpdated();
    }
    return res;
  },

  profile: () => api.get<{ success: boolean; user: AuthUser }>('/api/auth/profile'),

  logout: () => api.post<{ success: boolean }>('/api/auth/logout'),
};

// Backward-compatible aliases
export const signup = (name: string, email: string, password: string) => authApi.register(name, email, password);
export const login = (email: string, password: string) => authApi.login(email, password);
