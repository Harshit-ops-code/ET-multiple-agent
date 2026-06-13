// frontend/js/shortcuts.js
// Fix #24 — Ctrl+Enter triggers Generate from anywhere on the page
// Also exports skeleton show/hide helpers used by pipeline.js

// ── Keyboard shortcut ──────────────────────────────────────────────────────
document.addEventListener("keydown", (e) => {
  const isCtrlEnter = (e.ctrlKey || e.metaKey) && e.key === "Enter";
  if (!isCtrlEnter) return;

  // Don't fire if user is typing in a textarea (except the topic field)
  const active = document.activeElement;
  const isTextarea = active?.tagName === "TEXTAREA";
  const isTopicField = active?.id === "topic" || active?.id === "topicInput";

  if (isTextarea && !isTopicField) return;

  const btn = document.getElementById("generateBtn")
           || document.querySelector("button[id*='generate']")
           || document.querySelector(".btn-generate");

  if (btn && !btn.disabled) {
    btn.click();
  }
});

// ── Skeleton helpers ───────────────────────────────────────────────────────
// Call Skeleton.show() when pipeline starts, Skeleton.hide() when results arrive

const Skeleton = (() => {

  const BLOG_HTML = `
    <div class="skeleton-blog">
      <div class="skeleton skeleton-score"></div>
      <div class="skeleton skeleton-title"></div>
      <div class="skeleton skeleton-line long"></div>
      <div class="skeleton skeleton-line long"></div>
      <div class="skeleton skeleton-line medium"></div>
      <div class="skeleton skeleton-line long"></div>
      <div class="skeleton skeleton-line short"></div>
      <br/>
      <div class="skeleton skeleton-line long"></div>
      <div class="skeleton skeleton-line long"></div>
      <div class="skeleton skeleton-line medium"></div>
    </div>`;

  const SOCIAL_HTML = `
    <div class="skeleton-social">
      <div class="skeleton-card">
        <div class="skeleton skeleton-image"></div>
        <div class="skeleton skeleton-line medium"></div>
        <div class="skeleton skeleton-line long"></div>
        <div class="skeleton skeleton-line short"></div>
      </div>
      <div class="skeleton-card">
        <div class="skeleton skeleton-image"></div>
        <div class="skeleton skeleton-line medium"></div>
        <div class="skeleton skeleton-line long"></div>
        <div class="skeleton skeleton-line short"></div>
      </div>
    </div>`;

  function show() {
    _inject("tab-blog",    BLOG_HTML,   "skeletonBlog");
    _inject("tab-social",  SOCIAL_HTML, "skeletonSocial");
  }

  function hide() {
    _remove("skeletonBlog");
    _remove("skeletonSocial");
  }

  function _inject(tabId, html, skeletonId) {
    const tab = document.getElementById(tabId);
    if (!tab || document.getElementById(skeletonId)) return;
    const wrapper = document.createElement("div");
    wrapper.id = skeletonId;
    wrapper.innerHTML = html;
    tab.prepend(wrapper);
  }

  function _remove(skeletonId) {
    document.getElementById(skeletonId)?.remove();
  }

  return { show, hide };
})();
