export function StatusBadge({ value }: { value: string | undefined }) {
  const label = value ?? "unknown";
  const key = label.toLowerCase().replaceAll(" ", "-");
  return <span className={`badge ${key.includes("simulated") ? "simulated" : key.includes("demo") || key.includes("illustrative") ? "demo" : key.includes("unavailable") || key.includes("not_configured") || key.includes("not-configured") ? "unavailable" : "available"}`}>{label}</span>;
}

