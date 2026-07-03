import { useEffect, useState, type FormEvent } from 'react';
import { Bell, Settings, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { AlertBanner } from '@/components/ui/alert-banner';
import { LoadingButton } from '@/components/ui/loading-button';
import { platformApi, type Notification } from '@/api/platform';

export default function SettingsPage() {
  const [settings, setSettings] = useState<{ theme?: string; notifications?: boolean }>({});
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [markingId, setMarkingId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([platformApi.getSettings(), platformApi.listNotifications()])
      .then(([s, n]) => {
        setSettings(s.settings as typeof settings);
        setNotifications(n.notifications);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await platformApi.updateSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function markRead(id: number) {
    setMarkingId(id);
    try {
      await platformApi.markNotificationRead(id);
      const res = await platformApi.listNotifications();
      setNotifications(res.notifications);
    } finally {
      setMarkingId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Preferences and notifications" />
      <AlertBanner message={error} onDismiss={() => setError('')} />
      {saved && <AlertBanner message="Settings saved successfully." variant="success" />}

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={handleSave} className="card-surface space-y-5 p-6">
          <div className="flex items-center gap-2 text-slate-900">
            <Settings className="size-5 text-[#d26e41]" />
            <h2 className="font-semibold">Preferences</h2>
          </div>

          <label className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">
            <span className="text-sm text-slate-700">Email notifications</span>
            <input
              type="checkbox"
              checked={settings.notifications ?? true}
              onChange={(e) => setSettings((s) => ({ ...s, notifications: e.target.checked }))}
              className="size-4 rounded border-slate-300 text-[#d26e41] focus:ring-[#d26e41]/30"
            />
          </label>

          <label className="block">
            <span className="text-sm text-slate-700">Theme</span>
            <select
              value={settings.theme ?? 'light'}
              onChange={(e) => setSettings((s) => ({ ...s, theme: e.target.value }))}
              className="input-dark mt-1.5 w-full"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>

          <LoadingButton type="submit" loading={saving} loadingText="Saving...">Save Settings</LoadingButton>
        </form>

        <section className="card-surface p-6">
          <div className="mb-4 flex items-center gap-2">
            <Bell className="size-5 text-[#d26e41]" />
            <h2 className="font-semibold text-slate-900">Notifications</h2>
          </div>
          <ul className="space-y-2">
            {notifications.length === 0 ? (
              <li className="text-sm text-slate-500">No notifications</li>
            ) : (
              notifications.map((n) => (
                <li key={n.id} className={`rounded-xl border px-4 py-3 ${n.read ? 'border-slate-100 bg-slate-50/50' : 'border-[#d26e41]/20 bg-[#d26e41]/5'}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-slate-900">{n.title}</p>
                      <p className="mt-0.5 text-xs text-slate-600">{n.body}</p>
                    </div>
                    {!n.read && (
                      <button
                        type="button"
                        onClick={() => markRead(n.id)}
                        disabled={markingId === n.id}
                        className="inline-flex shrink-0 items-center gap-1 text-xs text-[#d26e41] hover:underline disabled:opacity-50"
                      >
                        {markingId === n.id && <Loader2 className="size-3 animate-spin" />}
                        Mark read
                      </button>
                    )}
                  </div>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>
    </div>
  );
}
