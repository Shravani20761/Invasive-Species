import { Bell, ChevronLeft, ChevronRight, LogOut, Radar, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import type { AlertItem, Page } from "../types";

const links = [
  { to: "/", label: "Overview", end: true },
  { to: "/submit", label: "Submit Sighting" },
  { to: "/identify", label: "Species Identification" },
  { to: "/map", label: "Spread Map" },
  { to: "/clusters", label: "Cluster Detection" },
  { to: "/analytics", label: "Analytics" },
  { to: "/alerts", label: "Alerts" },
  { to: "/verification", label: "Verification", roles: ["researcher", "admin"] },
  { to: "/species", label: "Species Database" },
  { to: "/settings", label: "Settings", roles: ["researcher", "admin"] },
];

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { user } = useAuth();
  return (
    <aside className={`flex shrink-0 flex-col bg-forest text-sage transition-all ${collapsed ? "w-[76px]" : "w-64"}`}>
      <div className="flex items-center gap-3 px-4 py-5">
        <Radar className="h-7 w-7 shrink-0 text-pale" />
        {!collapsed && (
          <div>
            <div className="font-display text-lg leading-5 text-white">Species Radar</div>
            <div className="text-xs text-pale/80">Early detection</div>
          </div>
        )}
      </div>
      <nav className="flex-1 space-y-1 px-2">
        {links
          .filter((link) => !link.roles || (user && link.roles.includes(user.role)))
          .map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              title={link.label}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${isActive ? "bg-pale font-semibold text-forest" : "text-sage hover:bg-white/10"}`
              }
            >
              {collapsed ? link.label.slice(0, 1) : link.label}
            </NavLink>
          ))}
      </nav>
      <button onClick={onToggle} className="m-3 flex items-center justify-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-pale">
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        {!collapsed && "Collapse"}
      </button>
    </aside>
  );
}

export function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="flex min-h-screen bg-sage">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function Topbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    api
      .get<Page<AlertItem>>("/api/alerts", { params: { status: "open", page_size: 5 } })
      .then((response) => setAlerts(response.data.items))
      .catch(() => setAlerts([]));
  }, []);

  return (
    <header className="flex items-center gap-4 border-b border-pale bg-white px-5 py-3">
      <form
        className="relative flex-1"
        onSubmit={(event) => {
          event.preventDefault();
          navigate(`/species?q=${encodeURIComponent(query)}`);
        }}
      >
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search the species catalogue"
          className="w-full rounded-lg border border-pale bg-sage/60 py-2 pl-9 pr-3 text-sm outline-none focus:border-deep"
        />
      </form>
      <div className="relative">
        <button className="relative rounded-lg p-2 hover:bg-sage" onClick={() => setOpen((value) => !value)} aria-label="Notifications">
          <Bell className="h-5 w-5" />
          {alerts.length > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-alert" />}
        </button>
        {open && (
          <div className="absolute right-0 z-20 mt-2 w-80 rounded-xl border border-pale bg-white p-3 shadow-card">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Open alerts</div>
            {alerts.length === 0 && <p className="text-sm text-muted">No open alerts.</p>}
            {alerts.map((alert) => (
              <button key={alert.id} className="block w-full rounded-lg px-2 py-2 text-left text-sm hover:bg-sage" onClick={() => navigate("/alerts")}>
                <div className="font-semibold">{alert.title}</div>
                <div className="text-xs capitalize text-muted">{alert.risk_level}</div>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="text-right">
        <div className="text-sm font-semibold">{user?.full_name}</div>
        <div className="text-xs capitalize text-muted">{user?.role.replace("_", " ")}</div>
      </div>
      <button onClick={logout} className="rounded-lg p-2 hover:bg-sage" aria-label="Log out">
        <LogOut className="h-5 w-5" />
      </button>
    </header>
  );
}
