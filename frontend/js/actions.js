// frontend/js/actions.js
// Fix #20 — copy buttons show "✓ Copied!" confirmation

function copyWithFeedback(text, buttonEl) {
  navigator.clipboard.writeText(text).then(() => {
    const original = buttonEl.textContent;
    buttonEl.textContent = "✓ Copied!";
    buttonEl.disabled = true;
    setTimeout(() => {
      buttonEl.textContent = original;
      buttonEl.disabled = false;
    }, 1500);
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);

    const original = buttonEl.textContent;
    buttonEl.textContent = "✓ Copied!";
    setTimeout(() => { buttonEl.textContent = original; }, 1500);
  });
}

function copyBlog(buttonEl) {
  const blog = document.getElementById("blogContent")?.innerText || "";
  copyWithFeedback(blog, buttonEl);
}

function copyBlogHtml(buttonEl) {
  const blogHtml = document.getElementById("blogContent")?.innerHTML || "";
  copyWithFeedback(blogHtml, buttonEl);
}

function copyCaption(platform, buttonEl) {
  const elNode = document.getElementById(`${platform}-caption`);
  copyWithFeedback(elNode?.innerText || "", buttonEl);
}

function downloadBlog() {
  const blog = document.getElementById("blogContent")?.innerText || "";
  const blob = new Blob([blog], { type: "text/plain" });
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(blob);
  a.download = "blog.txt";
  a.click();
  URL.revokeObjectURL(a.href);
}

// Image downloader helper
function downloadImgB64(b64, name) {
  const a = document.createElement('a');
  a.href = 'data:image/png;base64,' + b64;
  a.download = name + '.png';
  a.click();
}

function downloadImage(platform) {
  const img = platform === 'ig' ? document.getElementById('ig-image') : document.getElementById('li-image');
  const src = img?.src;
  if (!src || src.length < 10) { alert('No image available.'); return; }
  const a = document.createElement('a');
  a.href = src;
  a.download = platform + '_post.png';
  a.click();
}

// Fix #19 — "Post Now" and "Schedule" are now distinct functions
function postNow(platform) {
  alert(`Posting to ${platform} now... (wire up your social API here)`);
}

async function schedulePost(platform, buttonEl) {
  const jobId = State.get("jobId");
  const time  = document.getElementById("sched-time")?.value;
  const note  = document.getElementById("sched-note")?.value || "";

  if (!time) { alert("Please pick a schedule time first."); return; }

  buttonEl.disabled = true;
  buttonEl.textContent = "Scheduling...";

  try {
    const res  = await fetch(`${CONFIG.API}/api/schedule`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ job_id: jobId, platform, time, note }),
    });
    const data = await res.json();
    if (res.ok) {
      buttonEl.textContent = "✓ Scheduled!";
      setTimeout(() => {
        buttonEl.textContent = "Schedule Post";
        buttonEl.disabled = false;
      }, 2000);
      
      // Update schedule queue in state
      const item = { platform, time, note, title: "Social Post", status: "scheduled" };
      const queue = State.get("scheduleQueue") || [];
      queue.push(item);
      State.set("scheduleQueue", queue);
      Render.renderQueue();
    } else {
      throw new Error(data.detail || "Schedule failed");
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
    buttonEl.textContent = "Schedule Post";
    buttonEl.disabled = false;
  }
}

// ── IMAGE UPLOAD ──
function handleImageUpload(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    State.set("uploadedImageB64", e.target.result.split(',')[1]);
    const area = el('upload-area');
    if (area) {
      area.textContent = '✅ ' + file.name;
      area.classList.add('has-file');
    }
  };
  reader.readAsDataURL(file);
}

function getFormats() {
  return [...document.querySelectorAll('[data-fmt].checked')].map(item => item.dataset.fmt);
}
function getPlatforms() {
  return [...document.querySelectorAll('[data-platform].checked')].map(item => item.dataset.platform);
}

// ── GENERATE ──
async function generate() {
  const topic = el('topic')?.value.trim();
  if (!topic) { alert('Please enter a topic.'); return; }

  UI.showSpinner("Generating draft...");
  const errorBox = el('errorBox'); if (errorBox) errorBox.style.display = 'none';
  const approvedBanner = el('approvedBanner'); if (approvedBanner) approvedBanner.style.display = 'none';

  // Capture selected languages properly
  const langs = [...document.querySelectorAll('#lang-grid .check-item.checked')].map(item => item.dataset.lang);
  State.set("targetLanguages", langs);

  const body = {
    mode: State.get("mode"),
    topic,
    audience: el('audience')?.value.trim() || 'general professional audience',
    length: parseInt(el('length')?.value || "1000"),
    context: el('context')?.value.trim() || "",
    product_details: el('product_details')?.value.trim() || "",
    key_features: el('key_features')?.value.trim() || "",
    uvp: el('uvp')?.value.trim() || "",
    generate_images: el('gen-images')?.checked || false,
    image_formats: getFormats(),
    social_platforms: getPlatforms(),
    user_image_b64: State.get("uploadedImageB64") || null,
    target_languages: langs
  };

  try {
    const res = await fetch(`${CONFIG.API}/api/generate`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    State.set("jobId", data.job_id);
    Pipeline.start(data.job_id);
  } catch (err) {
    UI.showError('Cannot connect to backend. Make sure FastAPI server is running on port 8000.\n\n' + err.message);
  }
}
