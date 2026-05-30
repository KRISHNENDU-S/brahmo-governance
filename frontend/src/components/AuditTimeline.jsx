// AuditTimeline.jsx - shows the audit log as a timeline.
// This is the compliance evidence: every status change + every skip is here.

const ACTION_STYLE = {
  CASCADE_TRIGGER:  { icon: "🌊", color: "text-blue-700",  bg: "bg-blue-50" },
  STATUS_CHANGE:    { icon: "🔁", color: "text-amber-700", bg: "bg-amber-50" },
  CASCADE_SKIP:     { icon: "🔒", color: "text-red-700",   bg: "bg-red-50" },
  REVIEW_CONFIRMED: { icon: "✅", color: "text-green-700", bg: "bg-green-50" },
  SUPERSEDE:        { icon: "📄", color: "text-gray-700",  bg: "bg-gray-50" },
};

function fmtTime(ts) {
  try { return new Date(ts).toLocaleTimeString(); } catch { return ts; }
}

export default function AuditTimeline({ audit }) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h2 className="text-lg font-bold text-gray-800 mb-4">
        Audit Trail
        <span className="text-sm font-normal text-gray-400 ml-2">
          ({audit ? audit.length : 0})
        </span>
      </h2>

      {(!audit || audit.length === 0) ? (
        <div className="text-gray-400 text-sm">
          No audit entries yet. Trigger a cascade to populate.
        </div>
      ) : (
        <div className="space-y-2 max-h-[70vh] overflow-y-auto">
          {audit.map((e, i) => {
            const st = ACTION_STYLE[e.action] || ACTION_STYLE.STATUS_CHANGE;
            return (
              <div key={i} className={`border rounded-lg p-2 ${st.bg}`}>
                <div className="flex items-center gap-2">
                  <span>{st.icon}</span>
                  <span className={`text-xs font-bold ${st.color}`}>{e.action}</span>
                  {e.node_id && (
                    <span className="font-mono text-xs text-gray-500">{e.node_id}</span>
                  )}
                  <span className="text-[10px] text-gray-400 ml-auto">
                    {fmtTime(e.timestamp)}
                  </span>
                </div>
                {(e.old_value || e.new_value) && (
                  <div className="text-xs text-gray-600 mt-1">
                    {e.old_value} → {e.new_value}
                  </div>
                )}
                {e.reason && (
                  <div className="text-[11px] text-gray-500 mt-0.5 italic">{e.reason}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
