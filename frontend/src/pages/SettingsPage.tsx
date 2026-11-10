import { FormEvent, useEffect, useState } from "react";
import { PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { Page, User } from "../types";
import { formatDate } from "../utils/format";

type SettingsResponse = {
  settings: Record<string, number | boolean>;
  audit_logs: { id: number; action: string; entity_type: string; created_at: string }[];
};

const fields = [
  ["cluster_eps_km", "Cluster radius (km)"],
  ["cluster_min_samples", "Minimum sightings in a cluster"],
  ["alert_min_cluster_size", "Concentration alert size"],
  ["alert_growth_ratio", "Growth ratio threshold"],
  ["alert_new_area_km", "New-area distance (km)"],
  ["low_confidence_threshold", "Low-confidence threshold"],
] as const;

export function SettingsPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<Record<string, number | boolean>>({});
  const [audit, setAudit] = useState<SettingsResponse["audit_logs"]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [model, setModel] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  useEffect(() => {
    api.get<SettingsResponse>("/api/settings").then((response) => {
      setSettings(response.data.settings);
      setAudit(response.data.audit_logs);
    }).catch((err) => setError(errorMessage(err)));
    api.get("/api/ai/model").then((response) => setModel(response.data)).catch(() => setModel(null));
    if (user?.role === "admin") {
      api.get<Page<User>>("/api/users").then((response) => setUsers(response.data.items)).catch(() => setUsers([]));
    }
  }, [user?.role]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaved("");
    try {
      const response = await api.put<SettingsResponse>("/api/settings", settings);
      setSettings(response.data.settings);
      setSaved("Settings saved.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function changeRole(person: User, role: string) {
    await api.put(`/api/users/${person.id}`, { role });
    const response = await api.get<Page<User>>("/api/users");
    setUsers(response.data.items);
  }

  return (
    <div>
      <PageHeader title="Settings" subtitle="Cluster and alert thresholds apply the next time analysis runs. They do not change historical reviewed alerts." />
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      {saved && <p className="mb-3 text-sm text-deep">{saved}</p>}
      <div className="grid gap-5 xl:grid-cols-2">
        <form onSubmit={onSubmit} className="rounded-2xl bg-white p-5 shadow-card">
          <h2 className="font-semibold">Monitoring rules</h2>
          <div className="mt-4 space-y-3">
            {fields.map(([key, label]) => (
              <label key={key} className="block text-sm">
                {label}
                <input
                  type="number"
                  step="any"
                  disabled={user?.role !== "admin"}
                  className="mt-1 w-full rounded-lg border border-pale px-3 py-2"
                  value={Number(settings[key] ?? 0)}
                  onChange={(event) => setSettings({ ...settings, [key]: Number(event.target.value) })}
                />
              </label>
            ))}
          </div>
          {user?.role === "admin" && <button className="mt-4 rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white">Save settings</button>}
        </form>
        <section className="rounded-2xl bg-white p-5 shadow-card">
          <h2 className="font-semibold">Model in use</h2>
          {model && (
            <div className="mt-3 space-y-2 text-sm leading-6">
              <p><span className="font-semibold">Mode:</span> {String(model.inference_mode)}</p>
              <p><span className="font-semibold">Name:</span> {String(model.name)}</p>
              <p>{String(model.limitation || "")}</p>
              <p className="text-muted">Hold-out metric: {JSON.stringify(model.metrics)}</p>
            </div>
          )}
          {user?.role === "admin" && (
            <>
              <h2 className="mt-6 font-semibold">People</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {users.map((person) => (
                  <li key={person.id} className="flex items-center justify-between gap-3">
                    <span>{person.full_name}<span className="block text-xs text-muted">{person.email}</span></span>
                    <select className="rounded-lg border border-pale px-2 py-1" value={person.role} onChange={(event) => changeRole(person, event.target.value)}>
                      <option value="citizen">citizen</option>
                      <option value="researcher">researcher</option>
                      <option value="admin">admin</option>
                    </select>
                  </li>
                ))}
              </ul>
              <h2 className="mt-6 font-semibold">Recent audit</h2>
              <ul className="mt-3 space-y-1 text-sm text-muted">
                {audit.map((row) => <li key={row.id}>{formatDate(row.created_at)} · {row.action} · {row.entity_type}</li>)}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
