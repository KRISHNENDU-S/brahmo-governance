// CascadeTree.jsx - shows knowledge nodes as cards, colour-coded by status.
// REVIEW_REQUIRED nodes show review action buttons.
// Receives nodes + an onReview callback from App.

// status -> colour + label styling
const STATUS_STYLE = {
  ACTIVE:          { dot: "bg-green-500",  text: "text-green-700",  bg: "bg-green-50",  label: "ACTIVE" },
  REVIEW_REQUIRED: { dot: "bg-amber-500",  text: "text-amber-700",  bg: "bg-amber-50",  label: "REVIEW REQUIRED" },
  SUPERSEDED:      { dot: "bg-gray-400",   text: "text-gray-600",   bg: "bg-gray-50",   label: "SUPERSEDED" },
  EXPIRED:         { dot: "bg-gray-400",   text: "text-gray-500",   bg: "bg-gray-50",   label: "EXPIRED" },
  LEGAL_HOLD:      { dot: "bg-red-500",    text: "text-red-700",    bg: "bg-red-50",    label: "LEGAL HOLD" },
};

function NodeCard({ node, onReview }) {
  const st = STATUS_STYLE[node.status] || STATUS_STYLE.ACTIVE;
  const locked = node.status === "LEGAL_HOLD";

  return (
    <div className={`border rounded-lg p-3 ${st.bg} transition-all duration-300`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${st.dot}`} />
            <span className="font-mono text-xs text-gray-500">{node.id}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-600">
              {node.type}
            </span>
          </div>
          <div className="text-sm font-medium text-gray-800 mt-1">{node.title}</div>
          <div className={`text-xs font-semibold mt-1 ${st.text}`}>
            {locked && "🔒 "}{st.label}
          </div>
        </div>
      </div>

      {node.status === "REVIEW_REQUIRED" && (
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => onReview(node.id, "confirm")}
            className="text-xs px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700">
            Still valid
          </button>
          <button
            onClick={() => onReview(node.id, "expire")}
            className="text-xs px-2 py-1 rounded bg-gray-500 text-white hover:bg-gray-600">
            No longer relevant
          </button>
        </div>
      )}
    </div>
  );
}

export default function CascadeTree({ nodes, onReview }) {
  if (!nodes || nodes.length === 0)
    return <div className="text-gray-400">Loading nodes…</div>;

  // sort: REVIEW_REQUIRED first (so the cascade effect is obvious), then by id
  const sorted = [...nodes].sort((a, b) => {
    const pr = (s) => (s === "REVIEW_REQUIRED" ? 0 : s === "LEGAL_HOLD" ? 1 : 2);
    return pr(a.status) - pr(b.status) || a.id.localeCompare(b.id);
  });

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h2 className="text-lg font-bold text-gray-800 mb-4">
        Knowledge Nodes
        <span className="text-sm font-normal text-gray-400 ml-2">
          ({nodes.length})
        </span>
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[70vh] overflow-y-auto">
        {sorted.map((n) => (
          <NodeCard key={n.id} node={n} onReview={onReview} />
        ))}
      </div>
    </div>
  );
}
