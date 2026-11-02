"use client";

import { Activity, Database, FileWarning, GitBranch, Map, Mountain, Settings, ShieldAlert, Waves } from "lucide-react";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  ["/", "Situation Room", Map], ["/hazard-analysis", "Hazard Analysis", Mountain], ["/disaster-chain", "Disaster Chain", GitBranch],
  ["/impact-analysis", "Impact Analysis", Waves], ["/scenarios", "Scenario Studio", Activity], ["/incidents", "Incident Reports", FileWarning],
  ["/data-sources", "Data Sources", Database], ["/settings", "Settings & About", Settings],
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return <div className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark"><ShieldAlert size={19} /></span><span>HIMALAYAN<br />SENTINEL</span></div><nav className="nav">{links.map(([href, label, Icon]) => <Link className={pathname === href ? "active" : ""} href={href} key={href}><Icon size={16} />{label}</Link>)}</nav><p className="side-note">Experimental research prototype. It is not an official warning service or a substitute for local emergency authorities.</p></aside><main className="main">{children}</main></div>;
}

