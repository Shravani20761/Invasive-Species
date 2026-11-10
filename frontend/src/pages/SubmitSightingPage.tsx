import { FormEvent, useEffect, useState } from "react";
import { MapView } from "../components/MapView";
import { Badge, Notice, PageHeader } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { IdentifyResult, Sighting } from "../types";
import { formatPercent, localDateTimeValue, riskBadge } from "../utils/format";

export function SubmitSightingPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [category, setCategory] = useState("plant");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [locationName, setLocationName] = useState("");
  const [observedAt, setObservedAt] = useState(localDateTimeValue());
  const [submittedName, setSubmittedName] = useState("");
  const [notes, setNotes] = useState("");
  const [gpsNote, setGpsNote] = useState("Requesting location from this browser…");
  const [result, setResult] = useState<IdentifyResult | null>(null);
  const [saved, setSaved] = useState<Sighting | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!navigator.geolocation) {
      setGpsNote("This browser cannot share a location. Click the map or type coordinates.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setGpsNote("Location taken from this device. You can still move the point on the map.");
      },
      () => setGpsNote("Location permission was unavailable. Click the map or type coordinates."),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }, []);

  function chooseFile(next: File | null) {
    setFile(next);
    setSaved(null);
    setResult(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(next ? URL.createObjectURL(next) : "");
  }

  async function identify(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("image", file);
      body.append("category", category);
      const response = await api.post<IdentifyResult>("/api/ai/identify", body);
      setResult(response.data);
      if (!submittedName) setSubmittedName(response.data.predicted_common_name);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Choose a photograph first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("image", file);
      body.append("latitude", latitude);
      body.append("longitude", longitude);
      body.append("category", category);
      body.append("location_name", locationName);
      body.append("observed_at", new Date(observedAt).toISOString());
      body.append("submitted_name", submittedName);
      body.append("notes", notes);
      const response = await api.post<Sighting>("/api/sightings", body);
      setSaved(response.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const lat = Number(latitude);
  const lng = Number(longitude);
  const picked = Number.isFinite(lat) && Number.isFinite(lng) && latitude !== "" ? { latitude: lat, longitude: lng } : null;

  return (
    <div>
      <PageHeader title="Submit a sighting" subtitle="The photograph is checked by the identification service before it is stored. New reports stay pending until a researcher verifies them." />
      <Notice>The default model compares colour and texture with synthetic catalogue signatures. A low score means the image was not identified.</Notice>
      <div className="grid gap-5 xl:grid-cols-2">
        <form onSubmit={submit} className="space-y-4 rounded-2xl bg-white p-5 shadow-card">
          <label className="block text-sm font-semibold">Photograph</label>
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
          {preview && <img src={preview} alt="Selected sighting" className="h-48 w-full rounded-xl object-cover" />}
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-semibold">Category
              <select className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="plant">Plant</option>
                <option value="animal">Animal</option>
              </select>
            </label>
            <label className="text-sm font-semibold">Your species name
              <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" value={submittedName} onChange={(event) => setSubmittedName(event.target.value)} />
            </label>
          </div>
          <p className="text-xs text-muted">{gpsNote}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-semibold">Latitude
              <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" value={latitude} onChange={(event) => setLatitude(event.target.value)} required />
            </label>
            <label className="text-sm font-semibold">Longitude
              <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" value={longitude} onChange={(event) => setLongitude(event.target.value)} required />
            </label>
          </div>
          <label className="block text-sm font-semibold">Location name
            <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" value={locationName} onChange={(event) => setLocationName(event.target.value)} />
          </label>
          <label className="block text-sm font-semibold">Observed at
            <input type="datetime-local" className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" value={observedAt} onChange={(event) => setObservedAt(event.target.value)} required />
          </label>
          <label className="block text-sm font-semibold">Notes
            <textarea className="mt-1 w-full rounded-lg border border-pale px-3 py-2 font-normal" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} />
          </label>
          {error && <p className="text-sm text-alert">{error}</p>}
          <div className="flex gap-3">
            <button type="button" onClick={identify} disabled={busy || !file} className="rounded-lg border border-deep px-4 py-2 text-sm font-semibold text-deep disabled:opacity-50">Check with AI</button>
            <button disabled={busy} className="rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Working…" : "Submit sighting"}</button>
          </div>
        </form>
        <div className="space-y-4">
          <MapView
            height="320px"
            fit={false}
            picked={picked}
            onPick={(nextLat, nextLng) => {
              setLatitude(nextLat.toFixed(6));
              setLongitude(nextLng.toFixed(6));
              setGpsNote("Location set from the map.");
            }}
          />
          {result && (
            <div className="rounded-2xl bg-white p-4 shadow-card">
              <div className="text-xs uppercase tracking-wide text-muted">{result.inference_mode} model · {result.model_name}</div>
              <h2 className="mt-1 font-display text-2xl">{result.predicted_common_name}</h2>
              <p className="italic text-sm text-muted">{result.scientific_name}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge className={riskBadge(result.risk_level)}>{result.risk_level ?? "not assessed"}</Badge>
                <Badge className="bg-sage text-forest">{result.classification}</Badge>
                <Badge className="bg-slate-100 text-muted">{formatPercent(result.confidence)}</Badge>
              </div>
              <p className="mt-3 text-sm leading-6">{result.message}</p>
              <p className="mt-2 text-sm text-muted">{result.demo_notice}</p>
            </div>
          )}
          {saved && (
            <div className="rounded-2xl bg-white p-4 text-sm shadow-card">
              Sighting {saved.id} stored as {saved.verification_status}. Confidence {formatPercent(saved.confidence)}.
              {saved.insufficient_confidence && " The model flagged this result as low confidence."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
