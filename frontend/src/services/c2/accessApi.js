const hostname = typeof window === "undefined" ? "127.0.0.1" : window.location.hostname;
export const API_BASE = (import.meta.env?.VITE_API_BASE_URL || `http://${hostname}:8000`).replace(/\/+$/, "");
let csrf = "";

export class AccessError extends Error {
  constructor(message,status) { super(message); this.name = "AccessError"; this.status = status; }
}

export async function sessionFetch(url, options = {}) {
  const initialCSRF = csrf;
  const headers = new Headers(options.headers);
  if (!['GET','HEAD','OPTIONS'].includes((options.method || 'GET').toUpperCase()) && csrf) headers.set('X-CSRF-Token',csrf);
  const response = await fetch(url,{ ...options,credentials:'include',headers:Object.fromEntries(headers.entries()) });
  if (response.status === 401 && csrf === initialCSRF && !String(url).endsWith('/access/login')) {
    csrf = "";
    if (typeof window !== "undefined") window.dispatchEvent(new Event('c2:session-expired'));
  }
  return response;
}

export async function accessApi(path, { method = "GET", body, signal } = {}) {
  const initialCSRF = csrf;
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) abort();
  signal?.addEventListener("abort", abort, { once: true });
  const timeout = setTimeout(abort, 180000);
  try {
    const response = await sessionFetch(`${API_BASE}/api/c2/access${path}`, {
      method, credentials: "include", signal: controller.signal,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401) { throw new AccessError("Sign in required, or username/password incorrect.",401); }
      const message = typeof data?.detail === "string" ? data.detail : response.status === 422 ? "Check the required fields, coordinates and timezone." : "The access service could not complete the request.";
      throw new AccessError(message,response.status);
    }
    if (!data) throw new Error("Unreadable access-service response.");
    if (data.csrf_token && (path === "/login" || csrf === initialCSRF)) csrf = data.csrf_token;
    if (path === "/logout") csrf = "";
    return data;
  } catch (error) {
    if (signal?.aborted) throw new DOMException("Cancelled", "AbortError");
    if (controller.signal.aborted) throw new Error("Request timed out; try again.");
    if (error instanceof TypeError) throw new Error("Local access service unavailable. Start FastAPI and use the same hostname for frontend and backend.");
    throw error;
  } finally { clearTimeout(timeout); signal?.removeEventListener("abort", abort); }
}

export const selectionQuery = (site, node) => new URLSearchParams({ site_id: site, node_id: node }).toString();
