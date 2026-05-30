// PulseAlerts.jsx - shows targeted notifications, sorted by severity.
// Backend already returns them severity-sorted (URGENT first).

const SEVERITY = {
  URGENT:  { icon: "⛔", bg: "bg-red-50",    border: "border-red-300",    text: "text-red-700" },
  WARNING: { icon: "⚠️", bg: "bg-amber-50",  border: "border-amber-300",  text: "text-amber-700" },
  INFO:    { icon: "ℹ️", bg: "bg-blue-50",   border: "border-blue-300",   text: "text-blue-700" },
};

export default function PulseAlerts({ alerts }) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h2 className="text-lg font-bold text-gray-800 mb-4">
        Pulse Alerts
        <span className="text-sm font-normal text-gray-400 ml-2">
          ({alerts ? alerts.length : 0})
        </span>
      </h2>

      {(!alerts || alerts.length === 0) ? (
        <div className="text-gray-400 text-sm">
          No alerts. Trigger a cascade to notify affected doctors.
        </div>
      ) : (
        <div className="space-y-3 max-h-[70vh] overflow-y-auto">
          {alerts.map((a) => {
            const sev = SEVERITY[a.severity] || SEVERITY.INFO;
            return (
              <div key={a.id}
                   className={`border ${sev.border} ${sev.bg} rounded-lg p-3`}>
                <div className="flex items-center gap-2">
                  <span>{sev.icon}</span>
                  <span className={`text-xs font-bold ${sev.text}`}>{a.severity}</span>
                  <span className="text-xs text-gray-400 ml-auto">→ {a.user_name}</span>
                </div>
                <div className="text-sm font-medium text-gray-800 mt-1">{a.title}</div>
                <div className="text-xs text-gray-600 mt-1">{a.body}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
