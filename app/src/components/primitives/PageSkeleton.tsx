export function PageSkeleton() {
  return (
    <div className="page page-skeleton">
      <style>{`
        @keyframes sk-shimmer {
          0% { background-position: -600px 0; }
          100% { background-position: 600px 0; }
        }
        .sk {
          border-radius: 4px;
          background: linear-gradient(90deg, var(--surface-2) 25%, var(--line) 50%, var(--surface-2) 75%);
          background-size: 600px 100%;
          animation: sk-shimmer 1.4s ease-in-out infinite;
        }
      `}</style>

      <div style={{ marginBottom: 24 }}>
        <div className="sk" style={{ width: 90, height: 11, marginBottom: 10 }} />
        <div className="sk" style={{ width: "55%", height: 28, marginBottom: 8 }} />
        <div className="sk" style={{ width: "72%", height: 14 }} />
      </div>

      <div className="kpi-row" style={{ marginBottom: 20 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div className="kpi sk" key={i} style={{ minHeight: 88 }} />
        ))}
      </div>

      <div className="card card-pad sk" style={{ height: 220 }} />
    </div>
  );
}
