import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MapView } from "../components/MapView";
import { Badge, Notice, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { Overview, Page, Sighting } from "../types";
import { formatDate, formatPercent, riskBadge, statusBadge } from "../utils/format";

export function OverviewPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [sightings, setSightings] = useState<Sighting[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.get<Overview>("/api/analytics/overview"), api.get<Page<Sighting>>("/api/map/sightings", { params: { verification_status: "verified" } })])
      .then(([overview, map]) => {
        setData(overview.data);
        setSightings(map.data.items);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  const cards = [
    ["Verified sightings", data?.total_sightings ?? "—"],
    ["Invasive species detected", data?.invasive_species ?? "—"],
    ["Active clusters", data?.active_clusters ?? "—"],
    ["Open alerts", data?.open_alerts ?? "—"],
  ];

  return (
    <div>
      <PageHeader title={`Welcome, ${user?.full_name.split(" ")[0] ?? ""}`} subtitle="Official counts use verified sightings. Pending reports stay in the verification queue until a researcher accepts them." />
      {error && <p className="mb-4 text-sm text-alert">{error}</p>}
      {data?.data_notice && <Notice>{data.data_notice}</Notice>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-white p-4 shadow-card">
            <div className="text-sm text-muted">{label}</div>
            <div className="mt-2 font-display text-3xl">{value}</div>
          </div>
        ))}
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          {sightings.length === 0 ? (
            <div className="rounded-2xl bg-white p-6 text-sm text-muted shadow-card">No verified sightings to map yet.</div>
          ) : (
            <MapView sightings={sightings} height="420px" />
          )}
        </div>
        <div className="rounded-2xl bg-white p-4 shadow-card">
          <h2 className="font-semibold">Open alerts</h2>
          <div className="mt-3 space-y-3">
            {(data?.active_alerts ?? []).length === 0 && <p className="text-sm text-muted">No open alerts.</p>}
            {data?.active_alerts.map((alert) => (
              <Link key={alert.id} to="/alerts" className="block rounded-xl bg-sage px-3 py-2">
                <div className="text-sm font-semibold">{alert.title}</div>
                <Badge className={riskBadge(alert.risk_level)}>{alert.risk_level}</Badge>
              </Link>
            ))}
          </div>
          <h2 className="mt-5 font-semibold">Emerging clusters</h2>
          <div className="mt-3 space-y-2 text-sm">
            {(data?.emerging_clusters ?? []).length === 0 && <p className="text-muted">None in the current verified set.</p>}
            {data?.emerging_clusters.map((cluster) => (
              <div key={cluster.id} className="rounded-xl bg-sage px-3 py-2">
                {cluster.common_name} · {cluster.sighting_count} sightings
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-4 shadow-card">
          <h2 className="mb-3 font-semibold">Recent verified sightings</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-muted">
                <tr><th className="py-2">Species</th><th>When</th><th>Confidence</th><th>Status</th></tr>
              </thead>
              <tbody>
                {(data?.recent_sightings ?? []).map((sighting) => (
                  <tr key={sighting.id} className="border-t border-pale">
                    <td className="py-2">{sighting.common_name}</td>
                    <td>{formatDate(sighting.observed_at)}</td>
                    <td>{formatPercent(sighting.confidence)}</td>
                    <td><Badge className={statusBadge(sighting.verification_status)}>{sighting.verification_status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(data?.recent_sightings ?? []).length === 0 && <p className="py-6 text-sm text-muted">No verified sightings yet.</p>}
          </div>
        </div>
        <div className="rounded-2xl bg-white p-4 shadow-card">
          <h2 className="mb-3 font-semibold">Species distribution</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.species_distribution ?? []}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} height={70} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#1B513C" radius={4} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
