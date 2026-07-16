type Props = { percent?: number };

export default function WorkflowProgress({ percent = 0 }: Props) {
  const p = Math.max(0, Math.min(100, percent));
  return (
    <div>
      <div style={{ height: 10, background: "#e5e7eb", borderRadius: 999 }}>
        <div
          style={{
            width: `${p}%`,
            height: "100%",
            background: "#2563eb",
            borderRadius: 999,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <small>{p}%</small>
    </div>
  );
}