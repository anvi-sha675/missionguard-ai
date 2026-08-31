import { Routes, Route } from "react-router-dom";
import { MissionProvider } from "./store/MissionContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import TelemetryExplorer from "./pages/TelemetryExplorer";
import AnomalyCenter from "./pages/AnomalyCenter";
import MissionPlanner from "./pages/MissionPlanner";
import SpaceSituationalAwareness from "./pages/SpaceSituationalAwareness";
import Copilot from "./pages/Copilot";
import Reports from "./pages/Reports";

export default function App() {
  return (
    <MissionProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/telemetry" element={<TelemetryExplorer />} />
          <Route path="/anomalies" element={<AnomalyCenter />} />
          <Route path="/planner" element={<MissionPlanner />} />
          <Route path="/ssa" element={<SpaceSituationalAwareness />} />
          <Route path="/copilot" element={<Copilot />} />
          <Route path="/reports" element={<Reports />} />
        </Routes>
      </Layout>
    </MissionProvider>
  );
}
