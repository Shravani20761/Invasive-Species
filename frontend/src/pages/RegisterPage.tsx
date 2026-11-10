import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(fullName, email, password);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-sage p-6">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-2xl bg-white p-8 shadow-card">
        <h1 className="font-display text-3xl">Create an observer account</h1>
        <p className="mt-2 text-sm text-muted">New accounts are citizens. An administrator can later grant researcher access.</p>
        <label className="mt-6 block text-sm font-semibold">Full name</label>
        <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2" value={fullName} onChange={(event) => setFullName(event.target.value)} required minLength={2} />
        <label className="mt-4 block text-sm font-semibold">Email</label>
        <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2" value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        <label className="mt-4 block text-sm font-semibold">Password</label>
        <input className="mt-1 w-full rounded-lg border border-pale px-3 py-2" value={password} onChange={(event) => setPassword(event.target.value)} type="password" required minLength={8} />
        {error && <p className="mt-3 text-sm text-alert">{error}</p>}
        <button disabled={busy} className="mt-6 w-full rounded-lg bg-deep py-2.5 font-semibold text-white disabled:opacity-60">
          {busy ? "Creating account…" : "Create account"}
        </button>
        <p className="mt-4 text-sm text-muted">
          Already registered? <Link className="font-semibold text-deep" to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
