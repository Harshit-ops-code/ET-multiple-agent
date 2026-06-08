// frontend/js/state.js
// Fix #15 — controlled state manager instead of raw global object
// Fix #16 — el() helper instead of $ to avoid jQuery conflicts

// ── DOM helper ─────────────────────────────────────────────────────────────
// Named `el` instead of `$` to avoid shadowing jQuery if ever added
function el(id) {
  const node = document.getElementById(id);
  if (!node) console.warn(`el(): no element with id="${id}"`);
  return node;
}

// ── State manager ──────────────────────────────────────────────────────────
const State = (() => {
  const _state = {
    mode:             "news",
    jobId:            null,
    targetLanguages:  [],
    uploadedImageB64: null,
    data:             null,
    scheduleQueue:    []
  };

  function get(key) {
    return _state[key];
  }

  function set(key, value) {
    if (!(key in _state)) {
      console.warn(`State.set: unknown key "${key}"`);
    }
    _state[key] = value;
  }

  function reset() {
    _state.mode             = "news";
    _state.jobId            = null;
    _state.targetLanguages  = [];
    _state.uploadedImageB64 = null;
    _state.data             = null;
  }

  return { get, set, reset };
})();
