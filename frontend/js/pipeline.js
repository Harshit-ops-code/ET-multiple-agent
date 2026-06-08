// frontend/js/pipeline.js
// Fix #6  — error handling when fetch throws during polling
// Fix #13 — polling interval always cleaned up on error or completion

const Pipeline = (() => {
  let _pollInterval = null;
  let _consecutiveErrors = 0;
  const MAX_CONSECUTIVE_ERRORS = 3;

  function start(jobId) {
    // Always clear any previous interval before starting a new one
    stop();
    _consecutiveErrors = 0;

    _pollInterval = setInterval(() => _poll(jobId), CONFIG.POLL_INTERVAL_MS);
  }

  function stop() {
    if (_pollInterval !== null) {
      clearInterval(_pollInterval);
      _pollInterval = null;
    }
  }

  async function _poll(jobId) {
    try {
      const res = await fetch(`${CONFIG.API}/api/status/${jobId}`);

      // Fix #6: handle non-2xx responses explicitly
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      _consecutiveErrors = 0; // reset on success

      UI.updateProgress(data);

      if (data.status === "awaiting_human") {
        stop();
        Render.renderAll(data);
        UI.showResults();
        UI.showHumanGate(data);
        return;
      }

      if (data.status === "completed") {
        stop();
        Render.renderAll(data);
        UI.showResults();
        return;
      }

      if (data.status === "error") {
        stop();
        UI.showError(data.error || "An unknown error occurred.");
        return;
      }

    } catch (err) {
      // Fix #6: network errors no longer cause infinite silent spinning
      _consecutiveErrors++;
      console.error(`Poll error (${_consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS}):`, err);

      if (_consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        stop();
        UI.showError(
          "Lost connection to the server. Please check your network and try again."
        );
      }
      // else: retry on next tick
    }
  }

  return { start, stop };
})();
