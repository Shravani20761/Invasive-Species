import { useEffect, useState } from "react";
import { Badge, EmptyState, PageHeader } from "../components/ui";
import { api, errorMessage } from "../services/api";
import type { Page, Sighting } from "../types";
import { formatDate, formatPercent, riskBadge, statusBadge } from "../utils/format";

export function VerificationPage() {
  const [items, setItems] = useState<Sighting[]>([]);
  const [selected, setSelected] = useState<Sighting | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api.get<Page<Sighting>>("/api/verification/pending").then((response) => {
      setItems(response.data.items);
      setSelected((current) => response.data.items.find((item) => item.id === current?.id) ?? response.data.items[0] ?? null);
    }).catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(action: "approve" | "reject") {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await api.put(`/api/verification/${selected.id}/${action}`, { comment });
      setComment("");
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Verification" subtitle="Compare the photograph, the observer's name, and the model output. Only verified sightings enter the official monitoring counts." />
      {error && <p className="mb-3 text-sm text-alert">{error}</p>}
      {items.length === 0 ? (
        <EmptyState title="Nothing is waiting" body="Pending reports will appear here for review." />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
          <div className="space-y-2">
            {items.map((item) => (
              <button key={item.id} onClick={() => setSelected(item)} className={`w-full rounded-xl px-3 py-2 text-left text-sm ${selected?.id === item.id ? "bg-deep text-white" : "bg-white"}`}>
                <div className="font-semibold">{item.submitted_name || item.common_name}</div>
                <div className={selected?.id === item.id ? "text-pale" : "text-muted"}>{formatDate(item.observed_at)}</div>
              </button>
            ))}
          </div>
          {selected && (
            <article className="rounded-2xl bg-white p-5 shadow-card">
              <div className="grid gap-4 md:grid-cols-2">
                <img src={selected.image_url} alt="" className="h-64 w-full rounded-xl object-cover" />
                <div className="text-sm leading-6">
                  <div className="flex gap-2">
                    <Badge className={statusBadge(selected.verification_status)}>{selected.verification_status}</Badge>
                    {selected.is_demonstration && <Badge className="bg-amber-50 text-amber-700">Demonstration</Badge>}
                  </div>
                  <p className="mt-3"><span className="font-semibold">Observer name:</span> {selected.submitted_name || "—"}</p>
                  <p><span className="font-semibold">Model label:</span> {selected.prediction?.predicted_label || "—"}</p>
                  <p><span className="font-semibold">Scientific name:</span> {selected.prediction?.scientific_name || "—"}</p>
                  <p><span className="font-semibold">Confidence:</span> {formatPercent(selected.confidence)} {selected.insufficient_confidence && "(below threshold)"}</p>
                  <p><span className="font-semibold">Model:</span> {selected.prediction?.model_name} · {selected.prediction?.inference_mode}</p>
                  <p><span className="font-semibold">Location:</span> {selected.location_name} ({selected.latitude.toFixed(3)}, {selected.longitude.toFixed(3)})</p>
                  <p className="text-muted">{selected.notes}</p>
                  {selected.risk_level && <Badge className={riskBadge(selected.risk_level)}>{selected.risk_level}</Badge>}
                </div>
              </div>
              <label className="mt-4 block text-sm font-semibold">Review comment</label>
              <textarea className="mt-1 w-full rounded-lg border border-pale px-3 py-2 text-sm" rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
              <div className="mt-3 flex gap-3">
                <button disabled={busy} onClick={() => decide("approve")} className="rounded-lg bg-deep px-4 py-2 text-sm font-semibold text-white">Verify</button>
                <button disabled={busy} onClick={() => decide("reject")} className="rounded-lg border border-alert px-4 py-2 text-sm font-semibold text-alert">Reject</button>
              </div>
              {selected.verification_history.length > 0 && (
                <ul className="mt-4 space-y-2 text-sm">
                  {selected.verification_history.map((record) => (
                    <li key={record.id}>{formatDate(record.created_at)} · {record.reviewer_name} {record.action}: {record.comment}</li>
                  ))}
                </ul>
              )}
            </article>
          )}
        </div>
      )}
    </div>
  );
}
