import { useEffect, useState, type ReactElement } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { Overview, Species } from "../types";

const COLORS = ["#1B513C", "#123C2D", "#F59E0B", "#DC2626", "#64748B", "#3D7A5A"];

export function AnalyticsPage() {
  const { user } = useAuth();
  const [species, setSpecies] = useState<Species[]>([]);
  const [speciesId, setSpeciesId] = useState("");
  const [location, setLocation] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [includeUnverified, setIncludeUnverified] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trends, setTrends] = useState<{ daily: { date: string; count: number }[]; growth: { period: string; count: number; cumulative: number }[] }>({ daily: [], growth: [] });
  const [breakdown, setBreakdown] = useState<{ top_invasive: { name: string; count: number }[]; category_distribution: { name: string; value: number }[] }>({ top_invasive: [], category_distribution: [] });
  const [regions, setRegions] = useState<{ region: string; count: number }[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<{ items: Species[] }>("/api/species").then((response) => setSpecies(response.data.items)).catch(() => setSpecies([]));
  }, []);

  useEffect(() => {
    const params = {
      species_id: speciesId || undefined,
      location: location || undefined,
      start: start ? new Date(start).toISOString() : undefined,
      end: end ? new Date(end).toISOString() : undefined,
      include_unverified: user?.role === "admin" ? includeUnverified : false,
    };
    Promise.all([
      api.get<Overview>("/api/analytics/overview", { params }),
      api.get("/api/analytics/trends", { params }),
      api.get("/api/analytics/species", { params }),
      api.get("/api/analytics/regions", { params }),
    ])
      .then(([overviewResponse, trendResponse, speciesResponse, regionResponse]) => {
        setOverview(overviewResponse.data);
        setTrends(trendResponse.data);
        setBreakdown(speciesResponse.data);
        setRegions(regionResponse.data.regions);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)));
  }, [speciesId, location, start, end, includeUnverified, user?.role]);

  const cards = [
    ["Total sightings", overview?.total_sightings ?? 0],
    ["Invasive species", overview?.invasive_species ?? 0],
    ["Verified reports", overview?.verified_reports ?? 0],
    ["Active clusters", overview?.active_clusters ?? 0],
  ];

  return (
    <div>
      <PageHeader title="Spread analysis" subtitle="Every chart is calculated from database records. Rejected reports are excluded. Pending reports stay out unless an administrator asks for them." />
      <div className="mb-4 grid gap-3 rounded-2xl bg-white p-4 shadow-card md:grid-cols-5">
        <select className="rounded-lg border border-pale px-3 py-2 text-sm" value={speciesId} onChange={(event) => setSpeciesId(event.target.value)}>
          <option value="">All species</option>
          {species.map((item) => <option key={item.id} value={item.id}>{item.common_name}</option>)}
        </select>
        <input className="rounded-lg border border-pale px-3 py-2 text-sm" placeholder="Location contains" value={location} onChange={(event) => setLocation(event.target.value)} />
        <input type="date" className="rounded-lg border border-pale px-3 py-2 text-sm" value={start} onChange={(event) => setStart(event.target.value)} />
        <input type="date" className="rounded-lg border border-pale px-3 py-2 text-sm" value={end} onChange={(event) => setEnd(event.target.value)} />
        {user?.role === "admin" && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={includeUnverified} onChange={(event) => setIncludeUnverified(event.target.checked)} />
            Include pending
          </label>
        )}
      </div>
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={String(label)} className="rounded-2xl bg-white p-4 shadow-card">
            <div className="text-sm text-muted">{label}</div>
            <div className="mt-1 font-display text-3xl">{value}</div>
          </div>
        ))}
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <ChartCard title="Sightings over time">
          <LineChart data={trends.daily}>
            <CartesianGrid stroke="#E8F2E9" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#1B513C" strokeWidth={2} dot={false} />
          </LineChart>
        </ChartCard>
        <ChartCard title="Top reported invasive species">
          <BarChart data={breakdown.top_invasive}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} height={70} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#123C2D" radius={4} />
          </BarChart>
        </ChartCard>
        <ChartCard title="Category distribution">
          <PieChart>
            <Pie data={breakdown.category_distribution} dataKey="value" nameKey="name" outerRadius={90}>
              {breakdown.category_distribution.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
            </Pie>
            <Legend />
            <Tooltip />
          </PieChart>
        </ChartCard>
        <ChartCard title="Cumulative growth">
          <AreaChart data={trends.growth}>
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Area type="monotone" dataKey="cumulative" stroke="#1B513C" fill="#D0E5CE" />
          </AreaChart>
        </ChartCard>
        <ChartCard title="Region counts">
          <BarChart data={regions}>
            <XAxis dataKey="region" tick={{ fontSize: 10 }} interval={0} angle={-25} height={80} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#F59E0B" radius={4} />
          </BarChart>
        </ChartCard>
      </div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactElement }) {
  return (
    <section className="rounded-2xl bg-white p-4 shadow-card">
      <h2 className="mb-2 font-semibold">{title}</h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
    </section>
  );
}
