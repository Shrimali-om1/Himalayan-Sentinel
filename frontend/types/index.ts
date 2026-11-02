export type PointFeature = { id: string; name: string; category?: string; geometry: { type: string; coordinates: unknown }; classification?: string; [key: string]: unknown };
export type HazardCell = PointFeature & { rainfall_component: number; terrain_component: number; screening_score: number; screening_classification: string; classification: string; method: string };
export type Weather = { status?: string; classification?: string; rainfall_24h_mm: number | null; rainfall_72h_mm: number | null; forecast_24h_mm: number | null; latest_precipitation_mm: number | null; hourly: { time: string; precipitation: number | null }[]; notice: string; provider: string; timestamp: string; units?: string; timezone?: string };

