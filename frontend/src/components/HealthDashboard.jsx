// HealthDashboard.jsx - shows the 4-dimension health score + overall %.
// Receives the health state as a prop from App (so App controls refresh).
import React from "react";

// one labelled progress bar
function Bar({ label, value }) {
  const pct = Math.round(value * 100);
  // colour by health: green high, amber mid, red low
  const color = pct >= 75 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div className={`${color} h-2.5 rounded-full transition-all duration-500`}
             style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function HealthDashboard({ health }) {
  if (!health) return <div className="text-gray-400">Loading health…</div>;

  const s = health.score;
  const overallPct = Math.round(s.overall * 100);
  const overallColor =
    overallPct >= 75 ? "text-green-600" : overallPct >= 50 ? "text-amber-600" : "text-red-600";

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-800">Knowledge Health Score</h2>
        {health.deferred && (
          <span className="text-xs font-semibold px-2 py-1 rounded-full
                           bg-yellow-100 text-yellow-800 border border-yellow-300">
            PENDING REVIEW
          </span>
        )}
      </div>

      <div className={`text-4xl font-extrabold mb-4 ${overallColor}`}>
        {overallPct}%
        <span className="text-sm font-normal text-gray-400 ml-2">overall</span>
      </div>

      <Bar label="Coverage"    value={s.coverage} />
      <Bar label="Freshness"   value={s.freshness} />
      <Bar label="Balance"     value={s.balance} />
      <Bar label="Consistency" value={s.consistency} />

      {health.deferred && (
        <p className="text-xs text-gray-500 mt-3 italic">
          A cascade just ran. Score recomputes after the first review (or 24h) —
          shown now with a pending badge so the drop isn't mistaken for a quality problem.
        </p>
      )}
    </div>
  );
}
