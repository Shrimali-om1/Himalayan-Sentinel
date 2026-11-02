import type { Metadata } from "next";
import type { ReactNode } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = { title: "Himalayan Sentinel", description: "Experimental hazard screening and infrastructure impact dashboard" };

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

