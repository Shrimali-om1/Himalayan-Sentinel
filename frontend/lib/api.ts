export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
      cache: "no-store",
      signal: options?.signal ?? AbortSignal.timeout(10_000),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new Error(`API request timed out after 10 seconds (${path}).`);
    }
    throw new Error(`Unable to reach the API (${path}).`);
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try { detail = (await response.json()).detail ?? detail; } catch { /* retain status */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

