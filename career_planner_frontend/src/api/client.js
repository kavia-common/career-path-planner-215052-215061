/** Simple API client using fetch against the backend base URL. */

// PUBLIC_INTERFACE
export function apiBaseUrl() {
  /** Returns the base URL for backend API calls. */
  const base = process.env.REACT_APP_API_BASE_URL || "";
  return base.replace(/\/+$/, "");
}

// PUBLIC_INTERFACE
export async function apiGet(path) {
  /** Perform a GET request to the backend. */
  const url = `${apiBaseUrl()}${path}`;
  const res = await fetch(url, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} failed: ${res.status} ${text}`);
  }
  return res.json();
}
