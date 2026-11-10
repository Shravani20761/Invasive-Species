import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../types";

export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="grid min-h-screen place-items-center text-muted">Loading session…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="mx-auto max-w-lg p-8">
        <div className="rounded-2xl bg-white p-6 shadow-card">
          <h1 className="font-display text-2xl">This area is restricted</h1>
          <p className="mt-2 text-sm text-muted">Your role does not include this workspace. A researcher or administrator can open it.</p>
        </div>
      </div>
    );
  }
  return <Outlet />;
}
