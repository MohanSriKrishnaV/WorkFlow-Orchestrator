type Props = { status?: string | null };

const colorMap: Record<string, string> = {
  SUCCESS: "#166534",
  FAILED: "#991b1b",
  RUNNING: "#1d4ed8",
  QUEUED: "#92400e",
  PENDING: "#6b7280",
  CANCELLED: "#374151",
};

export default function StatusBadge({ status }: Props) {
  const s = (status ?? "UNKNOWN").toUpperCase();
  const color = colorMap[s] ?? "#111827";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        color: "white",
        background: color,
      }}
    >
      {s}
    </span>
  );
}