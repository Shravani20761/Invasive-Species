import { FormEvent, useEffect, useState } from "react";
import { Badge, Notice, PageHeader } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { IdentifyResult } from "../types";
import { formatPercent, riskBadge } from "../utils/format";

type Sample = { slug: string; common_name: string; category: string; image_url: string; notice: string };

export function IdentifyPage() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [category, setCategory] = useState("");
  const [result, setResult] = useState<IdentifyResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<{ items: Sample[] }>("/api/ai/samples").then((response) => setSamples(response.data.items)).catch(() => setSamples([]));
  }, []);

  async function useSample(sample: Sample) {
    const response = await fetch(sample.image_url);
    const blob = await response.blob();
    const next = new File([blob], `${sample.slug}.jpg`, { type: blob.type || "image/jpeg" });
    setFile(next);
    setPreview(sample.image_url);
    setCategory(sample.category);
    setResult(null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("image", file);
      if (category) body.append("category", category);
      const response = await api.post<IdentifyResult>("/api/ai/identify", body);
      setResult(response.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Species identification" subtitle="Upload a photograph or run one of the synthetic catalogue signatures. Results below the confidence threshold are marked unknown." />
      <Notice>Demo mode does not claim that a general-purpose model can name every invasive species. Replace the weights to leave demo mode.</Notice>
      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={onSubmit} className="rounded-2xl bg-white p-5 shadow-card">
          <label className="text-sm font-semibold">Demonstration signature</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {samples.map((sample) => (
              <button type="button" key={sample.slug} onClick={() => useSample(sample)} className="rounded-full bg-sage px-3 py-1 text-xs font-semibold">
                {sample.common_name}
              </button>
            ))}
          </div>
          <label className="mt-4 block text-sm font-semibold">Or upload a JPEG, PNG, or WebP</label>
          <input className="mt-2" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => {
            const next = event.target.files?.[0] ?? null;
            setFile(next);
            setPreview(next ? URL.createObjectURL(next) : "");
            setResult(null);
          }} />
          {preview && <img src={preview} alt="" className="mt-4 h-64 w-full rounded-xl object-cover" />}
          <label className="mt-4 block text-sm font-semibold">Pipeline</label>
          <select className="mt-1 rounded-lg border border-pale px-3 py-2" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Compare plant and animal pipelines</option>
            <option value="plant">Plants only</option>
            <option value="animal">Animals only</option>
          </select>
          {error && <p className="mt-3 text-sm text-alert">{error}</p>}
          <button disabled={busy || !file} className="mt-4 rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {busy ? "Analysing…" : "Identify"}
          </button>
        </form>
        <div className="rounded-2xl bg-white p-5 shadow-card">
          {!result && <p className="text-sm text-muted">The identification result will appear here, including the model name and confidence.</p>}
          {result && (
            <div>
              <div className="text-xs uppercase tracking-wide text-muted">{result.inference_mode} · {result.pipeline || result.category}</div>
              <h2 className="mt-1 font-display text-3xl">{result.insufficient_confidence ? "Insufficient confidence" : result.predicted_common_name}</h2>
              <p className="italic text-muted">{result.scientific_name}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge className="bg-sage text-forest">{formatPercent(result.confidence)}</Badge>
                <Badge className="bg-slate-100 text-muted">{result.classification}</Badge>
                <Badge className={riskBadge(result.risk_level)}>{result.risk_level ?? "not assessed"}</Badge>
              </div>
              <p className="mt-4 text-sm leading-6">{result.message}</p>
              <p className="mt-3 text-sm leading-6">{result.description}</p>
              <p className="mt-3 text-xs leading-5 text-muted">{result.demo_notice}</p>
              <h3 className="mt-4 text-sm font-semibold">Closest signatures</h3>
              <ul className="mt-2 space-y-1 text-sm">
                {result.alternatives.map((item) => (
                  <li key={item.scientific_name}>{item.common_name} · {formatPercent(item.confidence)}</li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted">{result.detections.note}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
