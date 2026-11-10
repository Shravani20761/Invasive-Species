import { useEffect, useState } from "react";
import { MapView } from "../components/MapView";
import { Badge, EmptyState, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { Cluster, Page } from "../types";
import { formatDate, riskBadge } from "../utils/format";

export function ClustersPage() {
  const { user } = useAuth();
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canRun = user?.role === "researcher" || user?.role === "admin";

  function load() {
    api.get<Page<Cluster>>("/api/clusters").then((response) => setClusters(response.data.items)).catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => {
    load();
  }, []);

  async function analyze() {
    setBusy(true);
    setError("");
    try {
      const response = await api.post<Page<Cluster> & { notice: string }>("/api/clusters/analyze");
      setClusters(response.data.items);
      setMessage(response.data.notice || `Formed ${response.data.total} clusters from verified sightings.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Cluster detection"
        subtitle="DBSCAN runs separately for each species, using a kilometre radius converted for the haversine distance. A cluster is not an alert by itself."
        action={canRun ? <button onClick={analyze} disabled={busy} className="rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Analysing…" : "Run analysis"}</button> : undefined}
      />
      {message && <p className="mb-3 text-sm text-deep">{message}</p>}
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      {clusters.length === 0 ? (
        <EmptyState title="No clusters yet" body="Verified sightings are clustered when a species has enough nearby points. A researcher can run the analysis after new reports are accepted." />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-3">
            {clusters.map((cluster) => (
              <article key={cluster.id} className="rounded-2xl bg-white p-4 shadow-card">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">{cluster.common_name}</h2>
                    <p className="text-sm italic text-muted">{cluster.scientific_name}</p>
                  </div>
                  <Badge className={riskBadge(cluster.risk_level)}>{cluster.risk_level}</Badge>
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div>Sightings: {cluster.sighting_count}</div>
                  <div className="capitalize">Growth: {cluster.growth_indicator}</div>
                  <div>Radius: {cluster.radius_km.toFixed(1)} km</div>
                  <div>Ratio: {cluster.growth_ratio.toFixed(2)}</div>
                  <div>First: {formatDate(cluster.first_detected)}</div>
                  <div>Latest: {formatDate(cluster.last_detected)}</div>
                </dl>
              </article>
            ))}
          </div>
          <MapView clusters={clusters} height="640px" fit />
        </div>
      )}
    </div>
  );
}
