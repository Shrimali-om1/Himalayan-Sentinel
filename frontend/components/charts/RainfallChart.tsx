"use client";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Weather } from "@/types";
export function RainfallChart({ weather }: { weather: Weather }) { return <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={weather.hourly}><defs><linearGradient id="rain" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#75b8ff" stopOpacity={.8}/><stop offset="1" stopColor="#75b8ff" stopOpacity={.05}/></linearGradient></defs><CartesianGrid stroke="#24443b" vertical={false}/><XAxis dataKey="time" tick={{ fill: "#91a3aa", fontSize: 11 }} axisLine={false} tickLine={false}/><YAxis tick={{ fill: "#91a3aa", fontSize: 11 }} axisLine={false} tickLine={false} unit=" mm"/><Tooltip contentStyle={{ background: "#0c201c", border: "1px solid #315447", borderRadius: 6 }}/><Area dataKey="precipitation" stroke="#75b8ff" fill="url(#rain)" strokeWidth={2}/></AreaChart></ResponsiveContainer></div>; }

