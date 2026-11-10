import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MapView } from "../components/MapView";
import { EmptyState, PageHeader } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { Cluster, Page, Sighting, Species } from "../types";

export function MapPage() {
  const [params] = useSearchParams();
  const [sightings, setSightings] = useState<Sighting[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [heatmap, setHeatmap] = useState<{ latitude: number; longitude: number; weight: number }[]>([]);
  const [species, setSpecies] = useState<Species[]>([]);
  const [speciesId, setSpeciesId] = useState(params.get("species_id") || "");
  const [classification, setClassification] = useState("");
  const [status, setStatus] = useState(params.get("status") || "");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Page<Species>>("/api/species").then((response) => setSpecies(response.data.items)).catch(() => setSpecies([]));
  }, []);

  useEffect(() => {
    const query = {
      species_id: speciesId || undefined,
      classification: classification || undefined,
      verification_status: status || undefined,
      start: start ? new Date(start).toISOString() : undefined,
      end: end ? new Date(end).toISOString() : undefined,
    };
    Promise.all([
      api.get<Page<Sighting>>("/api/map/sightings", { params: query }),
      api.get<Page<Cluster>>("/api/map/clusters", { params: { species_id: speciesId || undefined } }),
      api.get<{ items: { latitude: number; longitude: number; weight: number }[] }>("/api/map/heatmap", { params: query }),
    ])
      .then(([sightingResponse, clusterResponse, heatResponse]) => {
        setSightings(sightingResponse.data.items);
        setClusters(clusterResponse.data.items);
        setHeatmap(heatResponse.data.items);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)));
  }, [speciesId, classification, status, start, end]);

  return (
    <div>
      <PageHeader title="Spread map" subtitle="Markers come from stored sightings. Circle overlays are species clusters, and the pale discs show sighting density." />
      <div className="mb-4 grid gap-3 rounded-2xl bg-white p-4 shadow-card md:grid-cols-5">
        <select className="rounded-lg border border-pale px-3 py-2 text-sm" value={speciesId} onChange={(event) => setSpeciesId(event.target.value)}>
          <option value="">All species</option>
          {species.map((item) => <option key={item.id} value={item.id}>{item.common_name}</option>)}
        </select>
        <select className="rounded-lg border border-pale px-3 py-2 text-sm" value={classification} onChange={(event) => setClassification(event.target.value)}>
          <option value="">Invasive and native</option>
          <option value="invasive">Invasive</option>
          <option value="native">Native</option>
        </select>
        <select className="rounded-lg border border-pale px-3 py-2 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">Any status you can view</option>
          <option value="verified">Verified</option>
          <option value="pending">Pending</option>
          <option value="rejected">Rejected</option>
        </select>
        <input type="date" className="rounded-lg border border-pale px-3 py-2 text-sm" value={start} onChange={(event) => setStart(event.target.value)} />
        <input type="date" className="rounded-lg border border-pale px-3 py-2 text-sm" value={end} onChange={(event) => setEnd(event.target.value)} />
      </div>
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      {sightings.length === 0 && (
        <div className="mb-4">
          <EmptyState title="No sightings match these filters" body="The map is still available. Adjust the filters or submit a verified report to see markers." />
        </div>
      )}
      <MapView sightings={sightings} clusters={clusters} heatmap={heatmap} />
      <p className="mt-3 text-xs text-muted">{sightings.length} sightings · {clusters.length} clusters · map tiles © OpenStreetMap contributors</p>
    </div>
  );
}
