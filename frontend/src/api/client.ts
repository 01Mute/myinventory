const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type RequestBody = Record<string, unknown> | FormData | undefined;

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: RequestBody;
};

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, details: unknown) {
    super(formatError(details));
    this.status = status;
    this.details = details;
  }
}

function getCookie(name: string) {
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}

function formatError(details: unknown) {
  if (typeof details === "string") {
    return details;
  }
  if (details && typeof details === "object") {
    return Object.entries(details as Record<string, unknown>)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
      .join("\n");
  }
  return "요청을 처리하지 못했습니다.";
}

let csrfPromise: Promise<void> | null = null;

async function ensureCsrf() {
  if (!csrfPromise) {
    csrfPromise = fetch(`${API_BASE_URL}/auth/csrf/`, {
      credentials: "include"
    }).then((response) => {
      if (!response.ok) {
        throw new ApiError(response.status, "CSRF 토큰을 가져오지 못했습니다.");
      }
    }).catch((error) => {
      csrfPromise = null;
      throw error;
    });
  }
  return csrfPromise;
}

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

function isPaginated<T>(value: unknown): value is Paginated<T> {
  return Boolean(value) && typeof value === "object" && Array.isArray((value as Paginated<T>).results);
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return requestUrl<T>(`${API_BASE_URL}${path}`, options);
}

/**
 * Collect every page of a paginated list route into a single array.
 *
 * The UI builds location trees and pickers from complete lists, so it needs all
 * the rows; pagination exists to bound each individual response. Also accepts a
 * bare array so an unpaginated route keeps working.
 */
async function getAll<T>(path: string, options: RequestOptions = {}): Promise<T[]> {
  let payload = await request<Paginated<T> | T[]>(path, options);
  const collected: T[] = [];

  for (;;) {
    if (!isPaginated<T>(payload)) {
      return collected.concat(payload ?? []);
    }
    collected.push(...payload.results);
    if (!payload.next) {
      return collected;
    }
    payload = await requestUrl<Paginated<T>>(payload.next, options);
  }
}

async function requestUrl<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const unsafe = !["GET", "HEAD", "OPTIONS"].includes(method);

  if (unsafe) {
    await ensureCsrf();
  }

  const headers = new Headers(options.headers);
  const body = options.body;
  let requestBody: BodyInit | undefined;

  if (body instanceof FormData) {
    requestBody = body;
  } else if (body !== undefined) {
    headers.set("Content-Type", "application/json");
    requestBody = JSON.stringify(body);
  }

  const csrfToken = getCookie("csrftoken");
  if (unsafe && csrfToken) {
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(url, {
    ...options,
    method,
    credentials: "include",
    headers,
    body: requestBody
  });

  if (response.status === 204) {
    return null as T;
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }

  return data as T;
}

async function download(path: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include"
  });

  if (!response.ok) {
    const contentType = response.headers.get("Content-Type") ?? "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    throw new ApiError(response.status, data);
  }

  return response.blob();
}

export const api = {
  ensureCsrf,
  get: <T>(path: string) => request<T>(path),
  getAll,
  post: <T>(path: string, body?: RequestBody) =>
    request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: RequestBody) =>
    request<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  download
};

export function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return "요청을 처리하지 못했습니다.";
}
