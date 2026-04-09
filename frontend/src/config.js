// API Configuration
// Uses environment variables if set, otherwise uses production URLs
const isDev =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

export const API_URL = isDev
  ? "http://localhost:8001"
  : import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_BACKEND_API_URL ||
  "https://api.fixturecast.com";

export const ML_API_URL = isDev
  ? "http://localhost:8000"
  : import.meta.env.VITE_ML_API_URL ||
  import.meta.env.VITE_ML_API ||
  "https://ml.fixturecast.com";

// ML API Key for authenticated requests
export const ML_API_KEY = import.meta.env.VITE_ML_API_KEY || "";

// Authenticated fetch for ML API
export function mlApiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (ML_API_KEY) {
    headers["X-API-Key"] = ML_API_KEY;
  }
  return fetch(url, { ...options, headers });
}

// Export aliases for clarity
export const BACKEND_API_URL = API_URL;

// App URL for canonical links and OG tags
export const APP_URL = isDev
  ? "http://localhost:5173"
  : import.meta.env.VITE_APP_URL || "https://fixturecast.com";

export const API_ENDPOINTS = {
  // Backend API (port 8001)
  fixtures: `${API_URL}/api/fixtures`,
  standings: `${API_URL}/api/standings`,
  teams: `${API_URL}/api/teams`,
  team: (id) => `${API_URL}/api/team/${id}`,
  h2h: (homeId, awayId) => `${API_URL}/api/h2h/${homeId}/${awayId}`,
  live: `${API_URL}/api/live`,
  results: `${API_URL}/api/results`,

  // ML API (port 8000)
  prediction: (fixtureId) => `${ML_API_URL}/api/prediction/${fixtureId}`,
  health: `${ML_API_URL}/health`,
  feedback: `${ML_API_URL}/api/feedback`,
  performance: `${ML_API_URL}/api/feedback/performance`,
};

