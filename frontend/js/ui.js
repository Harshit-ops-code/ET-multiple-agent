// frontend/js/ui.js
// Custom Lexis AI dashboard logic with active stopwatch, logs telemetry, and mockups rendering

const UI = (() => {
  let _stopwatchInterval = null;
  let _stopwatchStart = 0;
  let _logStreamInterval = null;
  let _currentLogNode = null;
  let _logIndex = 0;

  const _nodeLogs = {
    starting: [
      { agent: "System", msg: "Initializing LangGraph multi-agent orchestration..." },
      { agent: "System", msg: "Establishing connections to LLM fallback model..." },
      { agent: "System", msg: "Allocating project workspace telemetry ports..." }
    ],
    web_search: [
      { agent: "Research", msg: "Triggering semantic index search across Chroma store..." },
      { agent: "Research", msg: "Executing web search query for topic validation..." },
      { agent: "Research", msg: "Re-ranking retrieved search documents (top 5)..." }
    ],
    write: [
      { agent: "Writer", msg: "Constructing outline blocks and target headings..." },
      { agent: "Writer", msg: "Drafting introduction section with keyword grounding..." },
      { agent: "Writer", msg: "Synthesizing main body copy paragraphs..." },
      { agent: "Writer", msg: "Generating concluding call-to-action sections..." }
    ],
    validate: [
      { agent: "Validator", msg: "Checking grammar, lexical variety, and syntax structures..." },
      { agent: "Validator", msg: "Calculating readability score index (target: Flesch)..." },
      { agent: "Validator", msg: "Verifying document word count constraints..." }
    ],
    rag: [
      { agent: "RAG Check", msg: "Extracting factual claims from draft for source comparison..." },
      { agent: "RAG Check", msg: "Verifying facts against retrieved search vectors..." },
      { agent: "RAG Check", msg: "Flagging ungrounded assertions for editor review..." }
    ],
    review: [
      { agent: "Reviewer", msg: "Starting 5-layer B2B brand compliance review..." },
      { agent: "Reviewer", msg: "Running tone matcher engine (conversational)..." },
      { agent: "Reviewer", msg: "Checking trademark and copyrighted brand names..." },
      { agent: "Reviewer", msg: "Scanning content safety policies compliance..." }
    ],
    gen_images: [
      { agent: "Image Maker", msg: "Translating content tags into visual SD prompts..." },
      { agent: "Image Maker", msg: "Invoking Stability AI API for image generation..." },
      { agent: "Image Maker", msg: "Rendering Blog Hero format (1080x1080, PNG)..." }
    ],
    gen_social: [
      { agent: "Social Agent", msg: "Drafting caption text with target hashtags..." },
      { agent: "Social Agent", msg: "Generating LinkedIn post format and graphics..." },
      { agent: "Social Agent", msg: "Generating Instagram mockups and layouts..." }
    ],
    localize: [
      { agent: "Localization", msg: "Spawning parallel translation subprocesses..." },
      { agent: "Localization", msg: "Translating approved draft to Spanish (ES)..." },
      { agent: "Localization", msg: "Translating approved draft to German (DE)..." }
    ]
  };

  // Stopwatch controls
  function startStopwatch() {
    stopStopwatch();
    _stopwatchStart = Date.now();
    _stopwatchInterval = setInterval(() => {
      const elapsed = Date.now() - _stopwatchStart;
      const seconds = (elapsed / 1000).toFixed(2);
      const elapsedEl = document.getElementById("loadingElapsed");
      if (elapsedEl) elapsedEl.textContent = `${seconds}s`;
    }, 30);
  }

  function stopStopwatch() {
    if (_stopwatchInterval) {
      clearInterval(_stopwatchInterval);
      _stopwatchInterval = null;
    }
    Pipeline3D.stop();
  }

  // Live Terminal Log Stream controls
  function appendLog(agent, message) {
    const logEl = document.getElementById("loadingLog");
    if (!logEl) return;
    const time = ((Date.now() - _stopwatchStart) / 1000).toFixed(2);
    const logItem = document.createElement("div");
    logItem.className = "loading-log-item";
    logItem.innerHTML = `
      <span class="loading-log-time">[${time}s]</span>
      <div class="loading-log-copy">
        <span class="loading-log-title">[${agent}]</span>
        <span class="loading-log-desc">${message}</span>
      </div>
    `;
    logEl.appendChild(logItem);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function startLogStream(node) {
    if (_currentLogNode === node) return;
    _currentLogNode = node;
    _logIndex = 0;

    if (_logStreamInterval) clearInterval(_logStreamInterval);

    const logs = _nodeLogs[node] || [
      { agent: "System", msg: `Executing node agent: ${node}...` }
    ];

    appendLog(logs[0].agent, logs[0].msg);
    _logIndex = 1;

    _logStreamInterval = setInterval(() => {
      if (_logIndex < logs.length) {
        appendLog(logs[_logIndex].agent, logs[_logIndex].msg);
        _logIndex++;
      } else {
        appendLog(logs[logs.length - 1].agent, "Awaiting backend response data...");
        clearInterval(_logStreamInterval);
      }
    }, 1600);
  }

  function stopLogStream() {
    if (_logStreamInterval) {
      clearInterval(_logStreamInterval);
      _logStreamInterval = null;
    }
    _currentLogNode = null;
    const logEl = document.getElementById("loadingLog");
    if (logEl) logEl.innerHTML = "";
  }

  // ── Human gate review ───────────────────────────────────────────────────────
  function showHumanGate(data) {
    document.getElementById("humanGateBanner")?.remove();

    const banner = document.createElement("div");
    banner.id = "humanGateBanner";
    banner.style.cssText = `
      position: sticky;
      top: 0;
      z-index: 100;
      background: var(--accent);
      color: #ffffff;
      padding: 14px 20px;
      border-radius: 10px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      box-shadow: var(--shadow-md);
    `;

    banner.innerHTML = `
      <div>
        <strong style="font-weight:700; font-size:13px;">👀 Human Review Required</strong>
        <div style="font-size:11px; opacity:0.9; margin-top:2px;">
          Quality: ${data.quality_score ?? "—"}/100 &nbsp;|&nbsp;
          Verdict: ${data.review_verdict ?? "pending"}
        </div>
      </div>
      <div style="display:flex; gap:8px; flex-shrink:0">
        <button id="btnApprove" style="
          background:#ffffff; color:var(--accent); border:none;
          padding:6px 14px; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer;">
          Approve
        </button>
        <button id="btnRefine" style="
          background:rgba(255,255,255,0.15); color:#ffffff; border:1px solid rgba(255,255,255,0.3);
          padding:6px 14px; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer;">
          Refine
        </button>
      </div>
    `;

    const container = document.getElementById("outputPanel") || document.body;
    container.prepend(banner);

    document.getElementById("btnApprove").onclick = () => submitFeedback("approve");
    document.getElementById("btnRefine").onclick = () => {
      const fb = prompt("What would you like changed?");
      if (fb) submitFeedback("refine", fb);
    };

    // Show bottom panel review gate for convenience/redundancy
    const gate = document.getElementById("humanGate");
    if (gate) {
      gate.style.setProperty("display", "block", "important");
      const iter = document.getElementById("iterInfo");
      if (iter) iter.textContent = `Iteration ${data.iteration || 1} of 3`;
    }
  }

  function hideHumanGate() {
    document.getElementById("humanGateBanner")?.remove();
    const gate = document.getElementById("humanGate");
    if (gate) {
      gate.style.setProperty("display", "none", "important");
      const feedback = document.getElementById("humanFeedback");
      if (feedback) feedback.value = "";
    }
  }

  async function submitFeedback(action, feedback = "") {
    const jobId = State.get("jobId");
    const langs = State.get("targetLanguages") || [];

    const btnApprove = document.getElementById("btnApprove");
    const btnRefine = document.getElementById("btnRefine");
    if (btnApprove) btnApprove.disabled = true;
    if (btnRefine) btnRefine.disabled = true;

    try {
      const res = await fetch(`${CONFIG.API}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, action, feedback, target_languages: langs }),
      });
      if (!res.ok) throw new Error("Feedback submission failed");

      hideHumanGate();
      const spinnerMsg = action === "refine" ? "Refining content..." : "Finalising content...";
      showSpinner(spinnerMsg);
      Pipeline.start(jobId);
    } catch (err) {
      showError(err.message);
    }
  }

  function showSpinner(msg = "Working...") {
    const elNode = document.getElementById("loadingStep");
    if (elNode) elNode.textContent = msg;

    stopLogStream();
    startStopwatch();

    // First display the panel container so client dimensions are computed
    document.getElementById("loadingState")?.classList.remove("hidden");
    document.getElementById("loadingState")?.style.setProperty("display", "flex", "important");
    document.getElementById("emptyState")?.classList.add("hidden");
    document.getElementById("emptyState")?.style.setProperty("display", "none", "important");
    document.getElementById("resultWrap")?.classList.add("hidden");
    document.getElementById("resultWrap")?.style.setProperty("display", "none", "important");

    // Launch the 3D Canvas visualizer loop
    Pipeline3D.start();
  }

  function showResults() {
    stopStopwatch();
    stopLogStream();
    document.getElementById("loadingState")?.classList.add("hidden");
    document.getElementById("loadingState")?.style.setProperty("display", "none", "important");
    document.getElementById("resultWrap")?.classList.remove("hidden");
    document.getElementById("resultWrap")?.style.setProperty("display", "flex", "important");
  }

  function showError(msg) {
    stopStopwatch();
    stopLogStream();
    const elNode = document.getElementById("errorBox");
    if (elNode) {
      elNode.textContent = msg;
      elNode.classList.remove("hidden");
      elNode.style.display = "block";
    } else {
      alert(`Error: ${msg}`);
    }
    document.getElementById("loadingState")?.classList.add("hidden");
    document.getElementById("loadingState")?.style.setProperty("display", "none", "important");
  }

  function updateProgress(data) {
    const nodeEl = document.getElementById("loadingStep");
    const currentNode = data.current_node || "starting";

    if (nodeEl) {
      const nodeLabels = {
        starting: '⏳ Initializing Workspace',
        web_search: '🌐 Researching Topic Context',
        write: '✍️ Drafting Articles',
        validate: '🔍 Checking Structure',
        rag: '🧠 Fact-Checking (RAG)',
        review: '🔒 Running Compliance Sweeps',
        gen_images: '🖼 Generating Layout Graphics',
        gen_social: '📱 Constructing Social Previews',
        human_review: '👤 Human Editorial Gate',
        localize: '🌍 Translating Content'
      };
      nodeEl.textContent = nodeLabels[currentNode] || currentNode || "";
      
      if (data.current_node) {
        startLogStream(data.current_node);
      }
    }

    // Set status of 3D Canvas visualizer nodes
    const nodeMapping = { write: 'write', validate: 'validate', rag: 'rag', review: 'review', gen_images: 'gen_images', gen_social: 'gen_social', localize: 'localize' };
    if (nodeMapping[currentNode]) {
      Pipeline3D.setActiveNode(nodeMapping[currentNode]);
    } else if (currentNode === "starting" || currentNode === "web_search") {
      Pipeline3D.setActiveNode("write");
    }

    // Update active node pulsing state classes
    const nodes = ["write", "validate", "rag", "review", "images", "social", "localize"];
    const listMapping = { write: 'write', validate: 'validate', rag: 'rag', review: 'review', gen_images: 'images', gen_social: 'social', localize: 'localize' };
    
    nodes.forEach(n => {
      const elNode = document.getElementById("ln-" + n);
      if (elNode) {
        elNode.className = "loading-node pending";
        if (listMapping[currentNode] === n) {
          elNode.className = "loading-node active";
        } else {
          const progressIndices = { write: 0, validate: 1, rag: 2, review: 3, gen_images: 4, gen_social: 5, localize: 6 };
          const activeIdx = progressIndices[listMapping[currentNode]] ?? -1;
          const currentIdx = progressIndices[n];
          if (activeIdx > currentIdx) {
            elNode.className = "loading-node done";
          }
        }
      }
    });

    // Update loading progress track
    const progressPercentMap = {
      starting: 8,
      web_search: 18,
      write: 38,
      validate: 52,
      rag: 68,
      review: 82,
      gen_images: 92,
      gen_social: 96,
      localize: 98
    };
    const percent = progressPercentMap[currentNode] || 6;
    const loadingPercentEl = document.getElementById("loadingPercent");
    const loadingProgressFillEl = document.getElementById("loadingProgressFill");
    if (loadingPercentEl) {
      loadingPercentEl.textContent = `${String(percent).padStart(2, '0')}%`;
    }
    if (loadingProgressFillEl) {
      loadingProgressFillEl.style.width = `${percent}%`;
    }

    // Update Telemetry Session statistics
    const mode = State.get("mode") || "news";
    const loadingModeStat = document.getElementById("loadingModeStat");
    if (loadingModeStat) {
      loadingModeStat.textContent = mode.toUpperCase();
    }

    const progressIndices = { starting: 0, web_search: 0, write: 1, validate: 2, rag: 3, review: 4, gen_images: 5, gen_social: 6, localize: 7 };
    const completedStagesCount = progressIndices[currentNode] || 0;
    const loadingStageStat = document.getElementById("loadingStageStat");
    if (loadingStageStat) {
      loadingStageStat.textContent = `${completedStagesCount} / 7`;
    }

    const langs = State.get("targetLanguages") || [];
    const loadingLangStat = document.getElementById("loadingLangStat");
    if (loadingLangStat) {
      loadingLangStat.textContent = String(langs.length);
    }

    const loadingStatusStat = document.getElementById("loadingStatusStat");
    if (loadingStatusStat) {
      loadingStatusStat.textContent = (data.status || "RUNNING").toUpperCase();
    }
  }

  // ── 3D CANVAS MATRIX ENGINE ──────────────────────────────────────────────────
  const Pipeline3D = (() => {
    let canvas, ctx, animationFrameId = null;
    let width, height;
    let rotationX = 0.3, rotationY = 0.5;
    let targetRotationX = 0.3, targetRotationY = 0.5;
    let isDragging = false;
    let startX = 0, startY = 0;
    
    // 7 agent nodes in 3D coordinate space
    const nodes = [
      { name: "Write", label: "✍️ Writer Agent", key: "write", x: 0, y: 0, z: 0, px: 0, py: 0 },
      { name: "Validate", label: "🔍 Validator Agent", key: "validate", x: 0, y: 0, z: 0, px: 0, py: 0 },
      { name: "RAG Check", label: "🧠 RAG Database", key: "rag", x: 0, y: 0, z: 0, px: 0, py: 0 },
      { name: "Review", label: "🔒 Compliance Sweeper", key: "review", x: 0, y: 0, z: 0, px: 0, py: 0 },
      { name: "Images", label: "🖼 Stable Diffusion", key: "gen_images", x: 0, y: 0, z: 0, px: 0, py: 0 },
      { name: "Social", label: "📱 Social Copywriter", key: "gen_social", x: 0, y: 0, z: 0, px: 0, py: 0 },
      { name: "Translate", label: "🌍 Engine Translator", key: "localize", x: 0, y: 0, z: 0, px: 0, py: 0 }
    ];

    // Data packets flowing between nodes
    const particles = [];
    const NUM_PARTICLES = 35;
    
    // Node status mapping (updated dynamically from updateProgress)
    let currentNodeIndex = -1;
    let nodeStatuses = {};

    function init() {
      canvas = document.getElementById("loading3DCanvas");
      if (!canvas) return;
      ctx = canvas.getContext("2d");
      resize();
      
      const radius = 95;
      nodes.forEach((node, i) => {
        const angle = (i / nodes.length) * Math.PI * 2;
        node.ox = radius * Math.cos(angle);
        node.oy = (i - 3) * 16;
        node.oz = radius * Math.sin(angle);
        node.x = node.ox;
        node.y = node.oy;
        node.z = node.oz;
      });

      particles.length = 0;
      for (let i = 0; i < NUM_PARTICLES; i++) {
        const fromIdx = Math.floor(Math.random() * nodes.length);
        const toIdx = (fromIdx + 1) % nodes.length;
        particles.push({
          from: fromIdx,
          to: toIdx,
          progress: Math.random(),
          speed: 0.006 + Math.random() * 0.008,
          size: 1.5 + Math.random() * 1.5,
          color: i % 2 === 0 ? "rgba(79, 70, 229, 0.4)" : "rgba(13, 148, 136, 0.3)"
        });
      }

      canvas.addEventListener("mousedown", handleMouseDown);
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      
      canvas.addEventListener("touchstart", handleTouchStart, { passive: true });
      window.addEventListener("touchmove", handleTouchMove, { passive: false });
      window.addEventListener("touchend", handleTouchEnd, { passive: true });
    }

    function resize() {
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    }

    function handleMouseDown(e) {
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
    }

    function handleMouseMove(e) {
      const rect = canvas.getBoundingClientRect();
      const mX = e.clientX - rect.left;
      const mY = e.clientY - rect.top;
      
      const hudCoords = document.getElementById("hudCoords");
      if (hudCoords) {
        hudCoords.textContent = `ROT: [${rotationX.toFixed(2)}, ${rotationY.toFixed(2)}]`;
      }

      if (isDragging) {
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        targetRotationY += dx * 0.008;
        targetRotationX += dy * 0.008;
        startX = e.clientX;
        startY = e.clientY;
      } else {
        const nx = (mX / width) - 0.5;
        const ny = (mY / height) - 0.5;
        targetRotationY = rotationY + nx * 0.05;
        targetRotationX = rotationX - ny * 0.05;
      }
    }

    function handleMouseUp() {
      isDragging = false;
    }
    
    function handleTouchStart(e) {
      if (e.touches.length === 1) {
        isDragging = true;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    }
    
    function handleTouchMove(e) {
      if (isDragging && e.touches.length === 1) {
        e.preventDefault();
        const dx = e.touches[0].clientX - startX;
        const dy = e.touches[0].clientY - startY;
        targetRotationY += dx * 0.01;
        targetRotationX += dy * 0.01;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
      }
    }
    
    function handleTouchEnd() {
      isDragging = false;
    }

    function setActiveNode(nodeKey) {
      currentNodeIndex = nodes.findIndex(n => n.key === nodeKey);
      
      nodes.forEach((node, idx) => {
        if (idx < currentNodeIndex) {
          nodeStatuses[node.key] = "done";
        } else if (idx === currentNodeIndex) {
          nodeStatuses[node.key] = "active";
        } else {
          nodeStatuses[node.key] = "pending";
        }
      });
    }

    function start() {
      if (!canvas) init();
      if (!canvas) return;
      
      stop();
      resize();
      
      let lastTime = performance.now();
      
      function tick(time) {
        // Double check for resizing if container layout completes late or window scales
        if (canvas && canvas.clientWidth > 0 && canvas.clientHeight > 0 && 
            (canvas.clientWidth !== width || canvas.clientHeight !== height)) {
          resize();
        }

        rotationX += (targetRotationX - rotationX) * 0.06;
        rotationY += (targetRotationY - rotationY) * 0.06;
        
        if (!isDragging) {
          targetRotationY += 0.002;
        }

        draw();
        animationFrameId = requestAnimationFrame(tick);
      }
      
      animationFrameId = requestAnimationFrame(tick);
    }

    function stop() {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
      if (canvas) {
        canvas.removeEventListener("mousedown", handleMouseDown);
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
        canvas.removeEventListener("touchstart", handleTouchStart);
        window.removeEventListener("touchmove", handleTouchMove);
        window.removeEventListener("touchend", handleTouchEnd);
      }
      canvas = null;
    }

    function draw() {
      ctx.clearRect(0, 0, width, height);
      
      const focalLength = 340;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.strokeStyle = "rgba(0, 0, 0, 0.015)";
      ctx.lineWidth = 1;
      const gridSpacing = 40;
      for (let x = gridSpacing; x < width; x += gridSpacing) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = gridSpacing; y < height; y += gridSpacing) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      const cosX = Math.cos(rotationX);
      const sinX = Math.sin(rotationX);
      const cosY = Math.cos(rotationY);
      const sinY = Math.sin(rotationY);

      nodes.forEach(node => {
        let x1 = node.ox * cosY - node.oz * sinY;
        let z1 = node.oz * cosY + node.ox * sinY;
        
        let y2 = node.oy * cosX - z1 * sinX;
        let z2 = z1 * cosX + node.oy * sinX;
        
        node.x = x1;
        node.y = y2;
        node.z = z2;

        const scale = focalLength / (focalLength + node.z);
        node.px = centerX + node.x * scale;
        node.py = centerY + node.y * scale;
        node.scale = scale;
      });

      particles.forEach(p => {
        p.progress += p.speed;
        if (p.progress >= 1) {
          p.progress = 0;
          const fromNode = nodes[p.from];
          const isDone = nodeStatuses[fromNode.key] === "done";
          const isActive = nodeStatuses[fromNode.key] === "active";
          
          if (isActive || isDone) {
            p.from = p.from;
            p.to = (p.from + 1) % nodes.length;
          } else {
            p.from = Math.floor(Math.random() * nodes.length);
            p.to = (p.from + 1) % nodes.length;
          }
        }

        const fromNode = nodes[p.from];
        const toNode = nodes[p.to];

        const x3d = fromNode.x + (toNode.x - fromNode.x) * p.progress;
        const y3d = fromNode.y + (toNode.y - fromNode.y) * p.progress;
        const z3d = fromNode.z + (toNode.z - fromNode.z) * p.progress;

        const scale = focalLength / (focalLength + z3d);
        p.px = centerX + x3d * scale;
        p.py = centerY + y3d * scale;
        p.scale = scale;
      });

      const renderQueue = [];
      nodes.forEach(n => renderQueue.push({ type: "node", z: n.z, item: n }));
      particles.forEach(p => renderQueue.push({ type: "particle", z: p.z, item: p }));
      
      renderQueue.sort((a, b) => b.z - a.z);

      ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(79, 70, 229, 0.04)";
      ctx.beginPath();
      for (let i = 0; i < nodes.length; i++) {
        const next = (i + 1) % nodes.length;
        ctx.moveTo(nodes[i].px, nodes[i].py);
        ctx.lineTo(nodes[next].px, nodes[next].py);
      }
      ctx.stroke();

      if (currentNodeIndex !== -1) {
        const activeNode = nodes[currentNodeIndex];
        nodes.forEach((n, idx) => {
          if (idx !== currentNodeIndex && nodeStatuses[n.key] !== "pending") {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(13, 148, 136, ${0.1 * n.scale})`;
            ctx.lineWidth = 1.5;
            ctx.moveTo(activeNode.px, activeNode.py);
            ctx.lineTo(n.px, n.py);
            ctx.stroke();
          }
        });
      }

      renderQueue.forEach(obj => {
        if (obj.type === "particle") {
          const p = obj.item;
          if (p.px > 0 && p.px < width && p.py > 0 && p.py < height) {
            ctx.beginPath();
            ctx.arc(p.px, p.py, p.size * p.scale, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();
          }
        } else {
          const n = obj.item;
          const status = nodeStatuses[n.key] || "pending";
          const radius = 6 * n.scale;

          ctx.beginPath();
          ctx.arc(n.px, n.py, radius, 0, Math.PI * 2);

          if (status === "done") {
            ctx.fillStyle = "rgb(5, 150, 105)";
            ctx.fill();
            
            ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
            ctx.lineWidth = 1;
            ctx.stroke();
          } else if (status === "active") {
            const pulse = 1 + 0.25 * Math.sin(performance.now() * 0.007);
            const activeRad = radius * pulse;
            
            ctx.beginPath();
            ctx.arc(n.px, n.py, activeRad * 2.2, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(79, 70, 229, 0.08)";
            ctx.fill();

            ctx.beginPath();
            ctx.arc(n.px, n.py, activeRad * 1.5, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(79, 70, 229, 0.18)";
            ctx.fill();

            ctx.beginPath();
            ctx.arc(n.px, n.py, radius, 0, Math.PI * 2);
            ctx.fillStyle = "rgb(79, 70, 229)";
            ctx.fill();
            
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();
          } else {
            ctx.fillStyle = "rgba(212, 212, 216, 0.8)";
            ctx.fill();
            
            ctx.strokeStyle = "rgba(0, 0, 0, 0.1)";
            ctx.lineWidth = 1;
            ctx.stroke();
          }

          ctx.font = `bold ${Math.max(8, Math.round(9 * n.scale))}px var(--font-sans)`;
          ctx.textAlign = "center";
          
          if (status === "active") {
            ctx.fillStyle = "rgb(9, 9, 11)";
            ctx.fillText(n.name, n.px, n.py - radius - 10);
            
            ctx.font = `${Math.max(7, Math.round(8 * n.scale))}px var(--font-mono)`;
            ctx.fillStyle = "rgb(79, 70, 229)";
            ctx.fillText("ACTIVE", n.px, n.py + radius + 12);
          } else if (status === "done") {
            ctx.fillStyle = "rgb(113, 113, 122)";
            ctx.fillText(n.name, n.px, n.py - radius - 8);
          } else {
            ctx.fillStyle = "rgba(161, 161, 170, 0.6)";
            ctx.fillText(n.name, n.px, n.py - radius - 6);
          }
        }
      });
    }

    return { init, start, stop, setActiveNode };
  })();

  return { showHumanGate, hideHumanGate, submitFeedback, showSpinner, showResults, showError, updateProgress, stopStopwatch, stopLogStream };
})();

// ── RENDER MODULE ──────────────────────────────────────────────────────────
const Render = (() => {
  function renderAll(data) {
    State.set("data", data);
    
    const blog = data.parsed_blog || {};
    const review = data.review_checks || {};
    
    const emptyState = el('emptyState'); if (emptyState) emptyState.style.display = 'none';
    const resultWrap = el('resultWrap'); if (resultWrap) resultWrap.style.display = 'flex';
    
    // Scores
    const qs = Math.round(data.quality_score || 0);
    const rs = data.review_score || 0;
    const rg = data.rag_score || 0;
    
    const scoreQuality = el('scoreQuality');
    if (scoreQuality) {
      scoreQuality.textContent = qs + '/100';
      scoreQuality.className = 'score-val ' + scoreClass(qs);
    }
    
    const scoreReview = el('scoreReview');
    if (scoreReview) {
      scoreReview.textContent = rs + '/100';
      scoreReview.className = 'score-val ' + scoreClass(rs);
    }
    
    const scoreRag = el('scoreRag');
    if (scoreRag) {
      scoreRag.textContent = rg + '/100';
      scoreRag.className = 'score-val ' + scoreClass(rg);
    }
    
    const scoreIter = el('scoreIter');
    if (scoreIter) scoreIter.textContent = (data.iteration || 1) + ' / 3';
    
    const vd = (data.review_verdict || 'APPROVED').toLowerCase().replace(' ','_');
    const verdictPill = el('verdictPill');
    if (verdictPill) {
      verdictPill.className = 'verdict-pill ' + vd;
      verdictPill.textContent = data.review_verdict || 'APPROVED';
    }

    // Banner
    const approvedBanner = el('approvedBanner');
    if (approvedBanner) {
      approvedBanner.style.display = data.approved ? 'block' : 'none';
    }

    // Blog
    const metaStrip = el('metaStrip');
    if (metaStrip) {
      metaStrip.innerHTML = '';
      if (data.mode) metaStrip.innerHTML += `<span class="meta-chip m">${data.mode.toUpperCase()}</span>`;
      if (blog.reading_time) metaStrip.innerHTML += `<span class="meta-chip t">⏱ ${blog.reading_time}</span>`;
      if (blog.target_cta) metaStrip.innerHTML += `<span class="meta-chip p">CTA: ${blog.target_cta}</span>`;
      metaStrip.innerHTML += `<span class="meta-chip g">Score: ${qs}/100</span>`;
    }

    const blogTitle = el('blogTitle'); if (blogTitle) blogTitle.textContent = blog.title || data.topic || '';
    const blogDesc = el('blogDesc'); if (blogDesc) blogDesc.textContent = blog.meta_description || '';
    const blogContent = el('blogContent'); if (blogContent) blogContent.innerHTML = marked(blog.content || data.raw_blog || '');

    const kwRow = el('kwRow');
    if (kwRow) {
      if (blog.seo_keywords && blog.seo_keywords.length) {
        kwRow.innerHTML = '<span class="kw-label">SEO:</span>' + blog.seo_keywords.map(k => `<span class="kw-tag">${k}</span>`).join('');
        kwRow.style.display = 'flex';
      } else {
        kwRow.style.display = 'none';
      }
    }

    const ctaBox = el('ctaBox');
    const ctaText = el('ctaText');
    if (ctaBox && ctaText) {
      if (blog.target_cta) {
        ctaText.textContent = blog.target_cta;
        ctaBox.style.display = 'block';
      } else {
        ctaBox.style.display = 'none';
      }
    }

    // Sources list
    const sources = data.sources || [];
    const sourcesPanel = el('sourcesPanel');
    const sourcesGrid = el('sourcesGrid');
    if (sourcesPanel && sourcesGrid) {
      if (sources.length) {
        sourcesPanel.style.display = 'block';
        sourcesGrid.innerHTML = sources.slice(0, 5).map(s => `
          <a class="source-card" href="${s.url||'#'}" target="_blank" rel="noopener">
            <div class="source-title">${esc(s.title||'Untitled')}</div>
            <div class="source-url">${esc(s.url||'')}</div>
          </a>`).join('');
      } else {
        sourcesPanel.style.display = 'none';
      }
    }

    // Review grid compliance indicators
    const reviewGrid = el('reviewGrid');
    if (reviewGrid) {
      const checks = { Tone: review.tone, Legal: review.legal, Brand: review.brand, Accuracy: review.accuracy, Policy: review.policy };
      reviewGrid.innerHTML = Object.entries(checks).map(([name, c]) => {
        if (!c) return '';
        const sc = c.score || 0;
        const col = sc >= 80 ? '#059669' : sc >= 60 ? '#d97706' : '#e11d48';
        const issues = (c.issues || []).map(i => `<div class="issue"><div class="issue-dot"></div>${esc(i)}</div>`).join('');
        return `<div class="review-card">
          <div class="review-card-header">
            <div class="review-card-name">${name}</div>
            <div class="review-score-ring" style="background:${col}10; color:${col}; border:2px solid ${col}30;">${sc}</div>
          </div>
          <div class="review-bar-track"><div class="review-bar-fill" style="width:${sc}%; background:${col};"></div></div>
          <div class="review-issues">${issues || '<span style="color:#059669; font-size:10px; font-weight:600;">✓ No issues</span>'}</div>
        </div>`;
      }).join('');
    }

    // RAG factual audits
    const ragVerdict = el('ragVerdict'); if (ragVerdict) {
      ragVerdict.textContent = data.rag_verdict || 'PASS';
      ragVerdict.className = 'rag-verdict ' + ((data.rag_verdict||'').toLowerCase() === 'pass' ? 'pass' : 'fail');
    }
    const ragSummary = el('ragSummary'); if (ragSummary) ragSummary.textContent = data.rag_summary || '';
    const ragSuggestions = el('ragSuggestions');
    if (ragSuggestions) {
      const sugs = data.rag_suggestions || [];
      ragSuggestions.innerHTML = sugs.map(s => `<div class="rag-sug"><span class="rag-sug-icon">→</span>${esc(s)}</div>`).join('');
    }

    // Required fixes list
    const fixes = data.review_fixes || [];
    const fixesSection = el('fixesSection');
    const fixesList = el('fixesList');
    if (fixesSection && fixesList) {
      if (fixes.length) {
        fixesSection.style.display = 'block';
        fixesList.innerHTML = fixes.map((f,i) => `<div class="fix-item"><span class="fix-num">#${i+1}</span>${esc(f)}</div>`).join('');
      } else {
        fixesSection.style.display = 'none';
      }
    }
    const editorNote = el('editorNote'); if (editorNote) editorNote.textContent = data.editor_note || 'No additional notes.';

    // Social mockup images and captions rendering
    const social = data.social_posts || {};
    const igImage = el('ig-image');
    const igCaption = el('ig-caption');
    if (social.instagram && igImage && igCaption) {
      igImage.src = 'data:image/png;base64,' + social.instagram.image_b64;
      igCaption.textContent = social.instagram.caption || '';
    }
    const liImage = el('li-image');
    const liCaption = el('li-caption');
    if (social.linkedin && liImage && liCaption) {
      liImage.src = 'data:image/png;base64,' + social.linkedin.image_b64;
      liCaption.textContent = social.linkedin.post_text || '';
    }

    // Generated images tab
    const images = data.images || {};
    const imgKeys = Object.keys(images);
    const imageGrid = el('imageGrid');
    if (imageGrid) {
      if (imgKeys.length) {
        imageGrid.innerHTML = imgKeys.map(fmt => {
          const img = images[fmt];
          return `<div class="image-card">
            <div class="image-card-header">
              <div class="image-card-label">${img.label||fmt}</div>
              <div class="image-card-size">${img.width}×${img.height}</div>
            </div>
            <img src="data:image/png;base64,${img.base64}" alt="${fmt}"/>
            <div class="image-card-footer">
              <button class="btn-small success" onclick="downloadImgB64('${img.base64}','${fmt}')">⬇ Download</button>
            </div>
          </div>`;
        }).join('');
      } else {
        imageGrid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--muted); font-size:12px;">No images generated yet.</div>`;
      }
    }

    // Translations list rendering
    const translationsWrap = el('translationsWrap');
    if (translationsWrap) {
      const localized = data.localized_content || {};
      const langKeys = Object.keys(localized);
      if (langKeys.length > 0) {
        translationsWrap.innerHTML = langKeys.map(lang => `
          <div class="review-card">
            <div style="font-weight:700; margin-bottom:10px; color:var(--text);">🌍 ${lang} Translation</div>
            <div style="font-size:13px; color:var(--text-secondary); line-height:1.7;">${marked(localized[lang])}</div>
          </div>
        `).join('');
      } else {
        const requestedLangs = data.target_languages || [];
        const isTranslating = data.current_node === 'localize' || (data.status === 'running' && requestedLangs.length > 0);
        translationsWrap.innerHTML = `<div class="review-card">
          <div style="font-weight:700; margin-bottom:8px; color:var(--text);">${isTranslating ? 'Translation in progress...' : 'No translations requested'}</div>
          <div style="font-size:12px; color:var(--muted); line-height:1.7;">
            ${isTranslating
              ? `Approved draft is being parallel translated into ${requestedLangs.join(', ')}. Each language takes 2-4 seconds to generate.`
              : 'Select languages in the sidebar before approving content to translate it here.'}
          </div>
        </div>`;
      }
    }

    // Connected Crumbs status updates
    const pipelineStages = ["write", "validate", "rag", "review", "images", "social", "localize"];
    const progressNodeMapping = { write: 0, validate: 1, rag: 2, review: 3, gen_images: 4, gen_social: 5, localize: 6 };
    const activeIndex = progressNodeMapping[data.current_node] ?? -1;

    pipelineStages.forEach((n, idx) => {
      const crumb = el('crumb-' + n);
      if (crumb) {
        crumb.className = 'crumb';
        if (idx < activeIndex || data.status === 'completed') {
          crumb.className = 'crumb done';
        } else if (idx === activeIndex) {
          crumb.className = 'crumb active';
        }
      }
    });

    // Stats bar label text
    const footerStats = el('footerStats'); if (footerStats) {
      footerStats.textContent = `Quality: ${qs}/100 · Review: ${rs}/100 · RAG: ${rg}/100 · Sources: ${sources.length}`;
    }
    const headerStatus = el('headerStatus'); if (headerStatus) {
      headerStatus.textContent = data.review_verdict === 'APPROVED' ? 'APPROVED' : 'AWAITING REVIEW';
    }
  }

  function renderQueue() {
    const q = el('scheduleQueue');
    if (!q) return;
    const queue = State.get("scheduleQueue") || [];
    if (!queue.length) { q.innerHTML = '<div style="text-align:center; padding:16px; color:var(--muted); font-size:11px;">No scheduled posts yet.</div>'; return; }
    q.innerHTML = queue.map(item => `
      <div class="queue-item">
        <span class="queue-platform">${{instagram:'📸', linkedin:'💼', both:'📱'}[item.platform]||'📱'}</span>
        <span class="queue-title">${esc(item.title)}</span>
        <span class="queue-time">${item.time}</span>
        <span class="queue-status ${item.status}">${item.status}</span>
      </div>`).join('');
  }

  function scoreClass(s) { return s >= 80 ? 'high' : s >= 60 ? 'mid' : 'low'; }
  function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function marked(md) {
    if (!md) return '';
    return md
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/^### (.+)$/gm,'<h3>$1</h3>')
      .replace(/^## (.+)$/gm,'<h2>$1</h2>')
      .replace(/^# (.+)$/gm,'<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,'<em>$1</em>')
      .replace(/`(.+?)`/g,'<code>$1</code>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank">$1</a>')
      .replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>')
      .replace(/^- (.+)$/gm,'<li>$1</li>')
      .replace(/(<li>.*<\/li>\n?)+/g,'<ul>$&</ul>')
      .replace(/\n\n/g,'</p><p>')
      .replace(/^(?!<[hbuiolpb])/gm,'')
      .replace(/^(.+)$/gm, l => l.startsWith('<') ? l : `<p>${l}</p>`);
  }

  return { renderAll, renderQueue, esc };
})();

// ── GLOBAL UI HANDLERS ─────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('active', ['blog','review','social','images','translations','schedule'][i]===name));
  ['blog','review','social','images','translations','schedule'].forEach(t => {
    const node = el('tab-'+t);
    if (node) node.classList.toggle('active', t===name);
  });
}

function showSocial(platform) {
  const ig = el('social-instagram'); if (ig) ig.style.display = platform === 'instagram' ? 'block' : 'none';
  const li = el('social-linkedin'); if (li) li.style.display = platform === 'linkedin' ? 'block' : 'none';
  document.querySelectorAll('.soc-tab').forEach(b => {
    b.classList.toggle('active', b.classList.contains(platform));
  });
}

function setMode(m) {
  State.set("mode", m);
  ['news','product'].forEach(n => {
    const btn = el('mode'+n[0].toUpperCase()+n.slice(1));
    if (btn) {
      btn.classList.toggle('active', m===n);
      btn.classList.toggle(n, true);
    }
  });
  const ps = el('product-section'); if (ps) ps.classList.toggle('hidden', m !== 'product');
  const nc = el('news-ctx'); if (nc) nc.style.display = m === 'news' ? 'block' : 'none';
  const tl = el('topic-label'); if (tl) tl.textContent = m === 'news' ? 'Topic / Idea *' : 'Product Name *';
}

function resetUI() {
  State.reset();
  Pipeline.stop();
  UI.hideHumanGate();
  UI.stopStopwatch();
  UI.stopLogStream();
  
  // Clear inputs
  const topic = el('topic'); if (topic) topic.value = '';
  const audience = el('audience'); if (audience) audience.value = '';
  const ctx = el('context'); if(ctx) ctx.value = '';
  const pd = el('product_details'); if(pd) pd.value = '';
  const kf = el('key_features'); if(kf) kf.value = '';
  const uvp = el('uvp'); if(uvp) uvp.value = '';
  
  // Clear UI state
  const resultWrap = el('resultWrap'); if (resultWrap) resultWrap.style.display = 'none';
  const approvedBanner = el('approvedBanner'); if (approvedBanner) approvedBanner.style.display = 'none';
  const errorBox = el('errorBox'); if (errorBox) errorBox.style.display = 'none';
  const emptyState = el('emptyState'); if (emptyState) emptyState.style.display = 'flex';
  const headerStatus = el('headerStatus'); if (headerStatus) headerStatus.textContent = 'READY';
  
  const crumbs = ["write", "validate", "rag", "review", "images", "social", "localize"];
  crumbs.forEach(n => {
    const crumb = el('crumb-'+n);
    if (crumb) crumb.className = 'crumb';
  });
}

// Initialise settings
setMode('news');
const schedTime = el('sched-time');
if (schedTime) {
  const defaultTime = new Date(); defaultTime.setHours(defaultTime.getHours()+1);
  schedTime.value = defaultTime.toISOString().slice(0, 16);
}

// Global Human review gate callback
window.humanAction = async function(action) {
  const feedback = document.getElementById("humanFeedback")?.value || "";
  await UI.submitFeedback(action, feedback);
};

// Toggle check-item visual active state when checkbox changes
document.addEventListener('change', (e) => {
  const input = e.target;
  if (input.tagName === 'INPUT' && input.type === 'checkbox') {
    const label = input.closest('.check-item');
    if (label) {
      label.classList.toggle('checked', input.checked);
    }
  }
});

// ── LOGIN / SIGNUP MODAL HANDLERS ──────────────────────────────────────────
let modalMode = "login";

window.openLoginModal = function() {
  document.getElementById("loginModal")?.classList.remove("hidden");
};

window.closeLoginModal = function() {
  document.getElementById("loginModal")?.classList.add("hidden");
};

window.toggleModalMode = function(e) {
  if (e) e.preventDefault();
  const title = document.getElementById("modalTitle");
  const subtitle = document.getElementById("modalSubtitle");
  const submitBtn = document.getElementById("modalSubmitBtn");
  const toggleText = document.getElementById("modalToggleText");
  const toggleLink = document.getElementById("modalToggleLink");
  
  if (modalMode === "login") {
    modalMode = "signup";
    if (title) title.textContent = "Create your Lexis AI account";
    if (subtitle) subtitle.textContent = "Get started with automated 6-node content pipelines";
    if (submitBtn) submitBtn.textContent = "Create Account";
    if (toggleText) toggleText.textContent = "Already have an account?";
    if (toggleLink) toggleLink.textContent = "Sign In";
  } else {
    modalMode = "login";
    if (title) title.textContent = "Welcome to Lexis AI";
    if (subtitle) subtitle.textContent = "Sign in to your account to generate and schedule articles";
    if (submitBtn) submitBtn.textContent = "Sign In";
    if (toggleText) toggleText.textContent = "Don't have an account?";
    if (toggleLink) toggleLink.textContent = "Create account";
  }
};

window.handleLoginSubmit = function(event) {
  if (event) event.preventDefault();
  const emailVal = document.getElementById("loginEmail")?.value || "User";
  
  let initials = "US";
  if (emailVal.includes("@")) {
    const namePart = emailVal.split("@")[0];
    if (namePart.includes(".") || namePart.includes("_") || namePart.includes("-")) {
      const parts = namePart.split(/[\._\-]/);
      initials = (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();
    } else if (namePart.length >= 2) {
      initials = namePart.substring(0, 2).toUpperCase();
    } else {
      initials = namePart.toUpperCase() + "S";
    }
  } else if (emailVal.length >= 2) {
    initials = emailVal.substring(0, 2).toUpperCase();
  }
  
  localStorage.setItem("isLoggedIn", "true");
  localStorage.setItem("userInitials", initials);
  localStorage.setItem("userEmail", emailVal);
  
  window.refreshLoginUI();
  window.closeLoginModal();

  // Auto enter app after successful login
  if (window.enterApp) {
    window.enterApp();
  }
};

window.refreshLoginUI = function() {
  const isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
  const initials = localStorage.getItem("userInitials") || "HA";
  
  const headerLoginBtn = document.getElementById("headerLoginBtn");
  const headerUserAvatar = document.getElementById("headerUserAvatar");
  const heroLoginBtn = document.getElementById("heroLoginBtn");
  const heroUserAvatar = document.getElementById("heroUserAvatar");
  
  const headerInitials = document.getElementById("headerAvatarInitials");
  const heroInitials = document.getElementById("heroAvatarInitials");
  
  if (isLoggedIn) {
    headerLoginBtn?.classList.add("hidden");
    headerUserAvatar?.classList.remove("hidden");
    heroLoginBtn?.classList.add("hidden");
    heroUserAvatar?.classList.remove("hidden");
    
    if (headerInitials) headerInitials.textContent = initials;
    if (heroInitials) heroInitials.textContent = initials;
  } else {
    headerLoginBtn?.classList.remove("hidden");
    headerUserAvatar?.classList.add("hidden");
    heroLoginBtn?.classList.remove("hidden");
    heroUserAvatar?.classList.add("hidden");
  }
};

window.checkLoginStatus = function() {
  window.refreshLoginUI();
};

window.handleAvatarClick = function() {
  if (confirm("Are you sure you want to sign out?")) {
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("userInitials");
    localStorage.removeItem("userEmail");
    window.refreshLoginUI();
    if (window.showHeroPage) {
      window.showHeroPage();
    }
  }
};

// Check login status on load
window.checkLoginStatus();

