// frontend/js/config.js
// Fix #5 — no more hardcoded localhost

const CONFIG = {
  // Automatically points to the right backend:
  // - localhost in dev
  // - same origin in production (FastAPI serves the frontend)
  API: window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : window.location.origin,

  POLL_INTERVAL_MS: 1500,
  MAX_ITERATIONS: 3,

  PLATFORMS: ["instagram", "linkedin", "twitter"],
  IMAGE_FORMATS: ["blog", "instagram", "linkedin"],
  LANGUAGES: ["Hindi", "Spanish", "French", "German", "Arabic", "Japanese"],
};
