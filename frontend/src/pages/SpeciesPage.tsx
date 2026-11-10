import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { api, errorMessage } from "../services/api";
import type { Page, Species } from "../types";
import { riskBadge } from "../utils/format";

const empty = {
  common_name: "",
  scientific_name: "",
  category: "plant",
  classification: "unknown",
  description: "",
  risk_level: "low",
  characteristics: "",
  distribution: "",
  reference_image: "",
};

export function SpeciesPage() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") || "");
  const [items, setItems] = useState<Species[]>([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState("");
  const isAdmin = user?.role === "admin";

  function load(search = query) {
    api.get<Page<Species>>("/api/species", { params: { q: search || undefined } }).then((response) => setItems(response.data.items)).catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => {
    load(params.get("q") || "");
    setQuery(params.get("q") || "");
  }, [params]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const payload = { ...form, reference_image: form.reference_image || null };
    try {
      if (editing) await api.put(`/api/species/${editing}`, payload);
      else await api.post("/api/species", payload);
      setForm(empty);
      setEditing(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(species: Species) {
    if (!window.confirm(`Delete ${species.common_name}?`)) return;
    try {
      await api.delete(`/api/species/${species.id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div>
      <PageHeader title="Species database" subtitle="The starting catalogue is a labelled demonstration set. Editing a record does not retrain the demo model." />
      <form className="mb-4 flex gap-2" onSubmit={(event) => { event.preventDefault(); load(); }}>
        <input className="w-full max-w-md rounded-lg border border-pale bg-white px-3 py-2 text-sm" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search common or scientific name" />
        <button className="rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white">Search</button>
      </form>
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="overflow-hidden rounded-2xl bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-sage text-xs uppercase text-muted">
              <tr><th className="px-4 py-3">Name</th><th>Category</th><th>Status</th><th>Risk</th><th>Sightings</th>{isAdmin && <th></th>}</tr>
            </thead>
            <tbody>
              {items.map((species) => (
                <tr key={species.id} className="border-t border-pale">
                  <td className="px-4 py-3">
                    <div className="font-semibold">{species.common_name}</div>
                    <div className="italic text-muted">{species.scientific_name}</div>
                    {species.is_demonstration && <div className="text-xs text-amber-700">Demonstration catalogue entry</div>}
                  </td>
                  <td className="capitalize">{species.category}</td>
                  <td className="capitalize">{species.classification}</td>
                  <td><Badge className={riskBadge(species.risk_level)}>{species.risk_level}</Badge></td>
                  <td>{species.sighting_count}</td>
                  {isAdmin && (
                    <td className="space-x-2 pr-3 text-right">
                      <button className="text-deep" onClick={() => {
                        setEditing(species.id);
                        setForm({
                          common_name: species.common_name,
                          scientific_name: species.scientific_name,
                          category: species.category,
                          classification: species.classification,
                          description: species.description,
                          risk_level: species.risk_level,
                          characteristics: species.characteristics,
                          distribution: species.distribution,
                          reference_image: species.reference_image || "",
                        });
                      }}>Edit</button>
                      <button className="text-alert" onClick={() => remove(species)}>Delete</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {isAdmin && (
          <form onSubmit={onSubmit} className="space-y-3 rounded-2xl bg-white p-4 shadow-card">
            <h2 className="font-semibold">{editing ? "Edit species" : "Add species"}</h2>
            {(["common_name", "scientific_name", "description", "characteristics", "distribution", "reference_image"] as const).map((field) => (
              <input key={field} className="w-full rounded-lg border border-pale px-3 py-2 text-sm" placeholder={field.replaceAll("_", " ")} value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} required={field === "common_name" || field === "scientific_name"} />
            ))}
            <select className="w-full rounded-lg border border-pale px-3 py-2 text-sm" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
              <option value="plant">Plant</option>
              <option value="animal">Animal</option>
            </select>
            <select className="w-full rounded-lg border border-pale px-3 py-2 text-sm" value={form.classification} onChange={(event) => setForm({ ...form, classification: event.target.value })}>
              <option value="invasive">Invasive</option>
              <option value="native">Native</option>
              <option value="unknown">Unknown</option>
            </select>
            <select className="w-full rounded-lg border border-pale px-3 py-2 text-sm" value={form.risk_level} onChange={(event) => setForm({ ...form, risk_level: event.target.value })}>
              {["low", "medium", "high", "critical"].map((level) => <option key={level}>{level}</option>)}
            </select>
            <button className="rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white">{editing ? "Save changes" : "Add species"}</button>
          </form>
        )}
      </div>
    </div>
  );
}
