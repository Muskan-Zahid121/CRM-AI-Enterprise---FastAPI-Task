export { getStoredUser, setAuthSession, clearAuthSession, getAuthToken } from '@/api/client';

export function dispatchAuthUserUpdated() {
  window.dispatchEvent(new Event('auth-user-updated'));
}
