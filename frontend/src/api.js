// In production the frontend (Cloudflare Pages) and backend (VPS) are on
// different origins, so relative fetch('/api/...') paths won't reach the
// backend. Set VITE_API_BASE_URL at build time to the backend's real URL
// (e.g. https://api.riffscribe.com); left unset, it defaults to '' so
// relative paths keep working through Vite's local dev proxy.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export function apiUrl(path) {
  return `${API_BASE_URL}${path}`
}
