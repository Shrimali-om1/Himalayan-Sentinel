import { StatusBadge } from "./StatusBadge";

export function PageHeader({ eyebrow, title, description, notice = "DEMO DATA — NOT A LIVE OBSERVATION. Review data provenance and limitations before interpreting results." }: { eyebrow: string; title: string; description: string; notice?: string }) {
  return <div className="topline"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p style={{ margin: 0 }}>{description}</p></div><div className="notice"><StatusBadge value="demo data" /> <span style={{ marginLeft: 7 }}>{notice}</span></div></div>;
}

