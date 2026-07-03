/** Backend base URL — set VITE_API_URL in frontend/.env */
export const API_BASE_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000';
