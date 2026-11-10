import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { AlertsPage } from "./pages/AlertsPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { ClustersPage } from "./pages/ClustersPage";
import { IdentifyPage } from "./pages/IdentifyPage";
import { LoginPage } from "./pages/LoginPage";
import { MapPage } from "./pages/MapPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { SubmitSightingPage } from "./pages/SubmitSightingPage";
import { VerificationPage } from "./pages/VerificationPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/submit" element={<SubmitSightingPage />} />
          <Route path="/identify" element={<IdentifyPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/clusters" element={<ClustersPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/species" element={<SpeciesPage />} />
          <Route element={<ProtectedRoute roles={["researcher", "admin"]} />}>
            <Route path="/verification" element={<VerificationPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
