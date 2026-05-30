// App.jsx - the brain: fetches data, holds state, handles actions, refreshes UI.
import { useState, useEffect } from "react";
import { getNodes, getHealth, getAlerts, getAudit, runCascade, review, resetDemo } from "./api";
import HealthDashboard from "./components/HealthDashboard";
import CascadeTree from "./components/CascadeTree";
import PulseAlerts from "./components/PulseAlerts";
import AuditTimeline from "./components/AuditTimeline";

// the node we supersede in the main demo (Sepsis v2)
const DEMO_SOURCE = "N-M08";

export default function App() {
  const [nodes, setNodes] = useState([]);
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  // fetch everything from the backend
  async function refresh() {
    const [n, h, a, au] = await Promise.all([getNodes(), getHealth(), getAlerts(), getAudit()]);
    setNodes(n);
    setHealth(h);
    setAlerts(a);
    setAudit(au);
  }

  // run once on first load
  useEffect(() => { refresh(); }, []);

  async function handleCascade() {
    setBusy(true);
    setMsg("");
    try {
      const res = await runCascade(DEMO_SOURCE);
      setMsg(`Cascade: ${res.cascade.affected.length} nodes flagged, ` +
             `${res.cascade.skipped.length} skipped, ${res.alerts_created} alerts sent.`);
      await refresh();
    } catch (e) {
      setMsg("Cascade failed: " + (e.response?.data?.detail || e.message));
    }
    setBusy(false);
  }

  async function handleReview(nodeId, action) {
    setBusy(true);
    try {
      await review(nodeId, action);
      setMsg(`Reviewed ${nodeId}: ${action}.`);
      await refresh();
    } catch (e) {
      setMsg("Review failed: " + (e.response?.data?.detail || e.message));
    }
    setBusy(false);
  }

  async function handleReset() {
    setBusy(true);
    await resetDemo();
    setMsg("Demo reset. All nodes ACTIVE.");
    await refresh();
    setBusy(false);
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      {/* header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-gray-800">
              BRAHMO Governance Engine
            </h1>
            <p className="text-sm text-gray-500">
              Cascade Invalidation · Health Score · Pulse Notifications
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleCascade}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-red-600 text-white font-medium
                         hover:bg-red-700 disabled:opacity-50">
              Supersede Sepsis v2 → Cascade
            </button>
            <button
              onClick={handleReset}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-gray-700 text-white font-medium
                         hover:bg-gray-800 disabled:opacity-50">
              Reset Demo
            </button>
          </div>
        </div>
        {msg && (
          <div className="mt-3 text-sm bg-white border rounded-lg px-3 py-2 text-gray-700">
            {msg}
          </div>
        )}
      </div>

      {/* four-column layout */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <HealthDashboard health={health} />
        </div>
        <div className="lg:col-span-1">
          <CascadeTree nodes={nodes} onReview={handleReview} />
        </div>
        <div className="lg:col-span-1">
          <PulseAlerts alerts={alerts} />
        </div>
        <div className="lg:col-span-1">
          <AuditTimeline audit={audit} />
        </div>
      </div>
    </div>
  );
}