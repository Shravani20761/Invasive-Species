import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Radar } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("citizen@example.com");
  const [password, setPassword] = useState("DemoCitizen#2026");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden bg-forest p-12 text-sage lg:block">
        <div className="flex items-center gap-3 text-white">
          <Radar className="h-8 w-8" />
          <span className="font-display text-2xl">Invasive Species Radar</span>
        </div>
        <p className="mt-10 max-w-md text-lg leading-8">
          Photograph a plant or animal, place it on the map, and follow how verified reports cluster over time.
        </p>
        <p className="mt-6 max-w-md text-sm leading-6 text-pale">
          The bundled identifier is a demo model trained on synthetic colour signatures. It is not a field-trained species detector.
        </p>
      </section>
      <section className="grid place-items-center bg-sage p-6">
        <form onSubmit={onSubmit} className="w-full max-w-md rounded-2xl bg-white p-8 shadow-card">
          <h1 className="font-display text-3xl">Sign in</h1>
          <p className="mt-2 text-sm text-muted">Use a demonstration account or your own citizen registration.</p>
          <label className="mt-6 block text-sm font-semibold">Email</label>
          <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2" value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          <label className="mt-4 block text-sm font-semibold">Password</label>
          <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2" value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
          {error && <p className="mt-3 text-sm text-alert">{error}</p>}
          <button disabled={busy} className="mt-6 w-full rounded-lg bg-deep py-2.5 font-semibold text-white disabled:opacity-60">
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="mt-4 text-sm text-muted">
            New observer? <Link className="font-semibold text-deep" to="/register">Create an account</Link>
          </p>
          <div className="mt-6 space-y-1 text-xs text-muted">
            <div>Citizen: citizen@example.com / DemoCitizen#2026</div>
            <div>Researcher: researcher@example.com / DemoResearch#2026</div>
            <div>Administrator: admin@example.com / DemoAdmin#2026</div>
          </div>
        </form>
      </section>
    </div>
  );
}
