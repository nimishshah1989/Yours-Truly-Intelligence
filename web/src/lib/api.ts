// Empty string → relative URL → goes through Nginx reverse proxy to backend
// Nginx injects the API key header so the frontend never needs it
const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").trim();

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: string,
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

function getRestaurantId(): string {
  if (typeof window === "undefined") return "5";
  return localStorage.getItem("ytip_restaurant_id") || "5";
}

export function setRestaurantId(id: number): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("ytip_restaurant_id", String(id));
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Restaurant-ID": getRestaurantId(),
    ...(options.headers as Record<string, string> || {}),
  };

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, res.statusText, body);
  }

  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
