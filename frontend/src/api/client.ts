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

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
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
