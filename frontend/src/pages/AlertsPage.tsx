import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, EmptyState, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { AlertItem, Page, Species } from "../types";
import { formatDate, riskBadge } from "../utils/format";

export function AlertsPage() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [species, setSpecies] = useState<Species[]>([]);
  const [risk, setRisk] = useState("");
  const [speciesId, setSpeciesId] = useState("");
  const [status, setStatus] = useState("open");
  const [error, setError] = useState("");
  const canReview = user?.role === "researcher" || user?.role === "admin";

  function load() {
    api
      .get<Page<AlertItem>>("/api/alerts", { params: { risk_level: risk || undefined, species_id: speciesId || undefined, status: status || undefined } })
      .then((response) => setAlerts(response.data.items))
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => {
    api.get<Page<Species>>("/api/species").then((response) => setSpecies(response.data.items)).catch(() => setSpecies([]));
  }, []);

  useEffect(() => {
    load();
  }, [risk, speciesId, status]);

  async function review(alert: AlertItem) {
    await api.put(`/api/alerts/${alert.id}/review`, { comment: "Reviewed in the dashboard." });
    load();
  }

  async function generate() {
    await api.post("/api/alerts/generate");
    load();
  }

  return (
    <div>
      <PageHeader
        title="Early warnings"
        subtitle="Alerts are raised by rules for concentration, growth, a species in a new area, or a verified invasive sighting inside a sensitive region."
        action={canReview ? <button onClick={generate} className="rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white">Refresh alerts</button> : undefined}
      />
      <div className="mb-4 flex flex-wrap gap-3">
        <select className="rounded-lg border border-pale bg-white px-3 py-2 text-sm" value={risk} onChange={(event) => setRisk(event.target.value)}>
          <option value="">All risk levels</option>
          {["low", "medium", "high", "critical"].map((item) => <option key={item}>{item}</option>)}
        </select>
        <select className="rounded-lg border border-pale bg-white px-3 py-2 text-sm" value={speciesId} onChange={(event) => setSpeciesId(event.target.value)}>
          <option value="">All species</option>
          {species.map((item) => <option key={item.id} value={item.id}>{item.common_name}</option>)}
        </select>
        <select className="rounded-lg border border-pale bg-white px-3 py-2 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">Any status</option>
          <option value="open">Open</option>
          <option value="reviewed">Reviewed</option>
        </select>
      </div>
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      {alerts.length === 0 ? (
        <EmptyState title="No alerts" body="Rules have not produced an alert for this filter. Finding a spatial cluster does not create an alert on its own." />
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <article key={alert.id} className="rounded-2xl bg-white p-4 shadow-card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">{alert.title}</h2>
                  <p className="text-sm text-muted">{alert.location_name} · {formatDate(alert.created_at)}</p>
                </div>
                <div className="flex gap-2">
                  <Badge className={riskBadge(alert.risk_level)}>{alert.risk_level}</Badge>
                  <Badge className="bg-slate-100 text-muted">{alert.alert_type.replaceAll("_", " ")}</Badge>
                </div>
              </div>
              <p className="mt-3 text-sm">{alert.description}</p>
              <p className="mt-2 text-sm text-muted"><span className="font-semibold text-forest">Reason: </span>{alert.reason}</p>
              <div className="mt-3 flex gap-3 text-sm">
                {alert.latitude != null && alert.longitude != null && (
                  <Link className="font-semibold text-deep" to={`/map?species_id=${alert.species_id ?? ""}`}>View on map</Link>
                )}
                {canReview && alert.status === "open" && (
                  <button className="font-semibold text-deep" onClick={() => review(alert)}>Mark reviewed</button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
