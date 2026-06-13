// frontend/js/effects.js
// Scroll reveals, parallax, empty-state mini orb, tab transitions

(function () {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ── Scroll reveal via IntersectionObserver ────────────────────────────────
  function initScrollReveal() {
    const selectors = ".reveal-on-scroll, .reveal-fade-left, .reveal-fade-right, .reveal-scale";

    if (prefersReducedMotion) {
      document.querySelectorAll(selectors).forEach((el) => el.classList.add("revealed"));
      return;
    }

    function reveal(el) {
      const delay = parseInt(el.dataset.revealDelay || "0", 10);
      setTimeout(() => el.classList.add("revealed"), delay);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          reveal(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -30px 0px" }
    );

    document.querySelectorAll(selectors).forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.92 && rect.bottom > 0) {
        reveal(el);
      } else {
        observer.observe(el);
      }
    });
  }

  // ── Hero scroll progress + parallax ───────────────────────────────────────
  function initHeroScrollEffects() {
    const heroPage = document.getElementById("hero-page");
    const progressFill = document.getElementById("heroScrollProgress");
    const leftCol = document.querySelector(".hero-left-column");
    const rightCol = document.querySelector(".hero-right-column");
    const featuresHeader = document.querySelector(".features-header");

    if (!heroPage) return;

    let ticking = false;

    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const maxScroll = Math.max(heroPage.scrollHeight - heroPage.clientHeight, 1);
        const progress = heroPage.scrollTop / maxScroll;

        if (progressFill) {
          progressFill.style.width = `${Math.min(progress * 100, 100)}%`;
        }

        if (!prefersReducedMotion) {
          const y = heroPage.scrollTop;
          if (leftCol) {
            leftCol.style.transform = `translateY(${y * 0.06}px)`;
          }
          if (rightCol) {
            rightCol.style.transform = `translateY(${y * -0.04}px) rotateY(${progress * 8}deg)`;
          }
          if (featuresHeader) {
            featuresHeader.style.transform = `translateY(${Math.max(0, (y - 200) * 0.03)}px)`;
          }
        }

        if (window.Avatar3D && typeof window.Avatar3D.setScrollProgress === "function") {
          window.Avatar3D.setScrollProgress(progress);
        }

        ticking = false;
      });
    }

    heroPage.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // ── Mini 3D orb for empty state ───────────────────────────────────────────
  const EmptyOrb = (() => {
    let canvas, ctx, animId = null;
    let width, height, visible = false;
    let rotationX = 0.35, rotationY = 0;
    let time = 0;
    let points = [];

    function buildPoints() {
      points = [];
      const numLat = 9;
      const numLng = 12;
      for (let lat = 1; lat < numLat; lat++) {
        const theta = (lat / numLat) * Math.PI;
        const sinTheta = Math.sin(theta);
        const cosTheta = Math.cos(theta);
        for (let lng = 0; lng < numLng; lng++) {
          const phi = (lng / numLng) * Math.PI * 2;
          points.push({
            ox: sinTheta * Math.cos(phi),
            oy: cosTheta,
            oz: sinTheta * Math.sin(phi),
            px: 0, py: 0, z: 0, scale: 1
          });
        }
      }
    }

    function resize() {
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    }

    function draw() {
      if (!ctx || !visible) return;
      ctx.clearRect(0, 0, width, height);

      time += 0.014;
      rotationY += 0.008;

      const cosX = Math.cos(rotationX);
      const sinX = Math.sin(rotationX);
      const cosY = Math.cos(rotationY);
      const sinY = Math.sin(rotationY);
      const cx = width / 2;
      const cy = height / 2;
      const r = Math.min(width, height) * 0.32;

      points.forEach((p) => {
        const morph = Math.sin(p.ox * 3 + time) * 4;
        const sx = p.ox * (r + morph);
        const sy = p.oy * (r + morph);
        const sz = p.oz * (r + morph);

        const x1 = sx * cosY - sz * sinY;
        const z1 = sx * sinY + sz * cosY;
        const y2 = sy * cosX - z1 * sinX;
        const z2 = sy * sinX + z1 * cosX;

        const f = 200;
        const scale = f / (f + z2);
        p.px = cx + x1 * scale;
        p.py = cy + y2 * scale;
        p.z = z2;
        p.scale = scale;
      });

      // Energy ring
      ctx.beginPath();
      ctx.ellipse(cx, cy, r * 1.15, r * 0.45, rotationY * 0.5, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(79, 70, 229, ${0.12 + Math.sin(time * 2) * 0.06})`;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Mesh lines
      ctx.lineWidth = 0.4;
      for (let i = 0; i < points.length; i++) {
        const p1 = points[i];
        let connects = 0;
        for (let j = i + 1; j < points.length; j++) {
          const p2 = points[j];
          const d = (p1.ox - p2.ox) ** 2 + (p1.oy - p2.oy) ** 2 + (p1.oz - p2.oz) ** 2;
          if (d < 0.1) {
            const alpha = Math.max(0.05, 0.2 - p1.z / 300);
            ctx.beginPath();
            ctx.moveTo(p1.px, p1.py);
            ctx.lineTo(p2.px, p2.py);
            ctx.strokeStyle = `rgba(13, 148, 136, ${alpha})`;
            ctx.stroke();
            if (++connects > 2) break;
          }
        }
      }

      // Nodes
      [...points].sort((a, b) => b.z - a.z).forEach((p) => {
        const alpha = Math.max(0.15, 0.75 - p.z / 200);
        ctx.beginPath();
        ctx.arc(p.px, p.py, p.scale * 1.4, 0, Math.PI * 2);
        ctx.fillStyle = p.z < 0
          ? `rgba(13, 148, 136, ${alpha})`
          : `rgba(79, 70, 229, ${alpha})`;
        ctx.fill();
      });

      // Core
      const pulse = 1 + Math.sin(time * 3) * 0.08;
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 18 * pulse);
      grad.addColorStop(0, "rgba(79, 70, 229, 0.35)");
      grad.addColorStop(1, "rgba(79, 70, 229, 0)");
      ctx.beginPath();
      ctx.arc(cx, cy, 18 * pulse, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      ctx.font = "700 11px 'Plus Jakarta Sans', sans-serif";
      ctx.fillStyle = "rgba(79, 70, 229, 0.9)";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("LX", cx, cy);

      animId = requestAnimationFrame(draw);
    }

    function start() {
      if (animId || prefersReducedMotion) return;
      visible = true;
      draw();
    }

    function stop() {
      visible = false;
      if (animId) {
        cancelAnimationFrame(animId);
        animId = null;
      }
    }

    function init() {
      canvas = document.getElementById("empty-state-orb");
      if (!canvas) return;
      ctx = canvas.getContext("2d");
      buildPoints();
      resize();
      window.addEventListener("resize", resize);

      canvas.addEventListener("mousedown", (e) => {
        const startX = e.clientX;
        const startY = e.clientY;
        const startRotY = rotationY;
        const startRotX = rotationX;
        function onMove(ev) {
          rotationY = startRotY + (ev.clientX - startX) * 0.012;
          rotationX = startRotX + (ev.clientY - startY) * 0.012;
        }
        function onUp() {
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
        }
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });

      const emptyState = document.getElementById("emptyState");
      if (!emptyState) return;

      const obs = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting && emptyState.style.display !== "none") {
              start();
              pulsePipelineSteps();
            } else {
              stop();
            }
          });
        },
        { threshold: 0.2 }
      );
      obs.observe(emptyState);
    }

    return { init, start, stop };
  })();

  // ── Sequential glow on empty pipeline steps ───────────────────────────────
  function pulsePipelineSteps() {
    if (prefersReducedMotion) return;
    const steps = document.querySelectorAll(".empty-pipeline-step");
    if (!steps.length) return;

    let idx = 0;
    const interval = setInterval(() => {
      steps.forEach((s, i) => s.classList.toggle("is-lit", i === idx));
      idx = (idx + 1) % steps.length;
    }, 900);

    const emptyState = document.getElementById("emptyState");
    const stopObs = new MutationObserver(() => {
      if (emptyState.style.display === "none" || emptyState.classList.contains("hidden")) {
        clearInterval(interval);
        steps.forEach((s) => s.classList.remove("is-lit"));
        stopObs.disconnect();
      }
    });
    stopObs.observe(emptyState, { attributes: true, attributeFilter: ["style", "class"] });
  }

  // ── Tab switch animation hook ─────────────────────────────────────────────
  function initTabAnimations() {
    const originalSwitch = window.switchTab;
    if (typeof originalSwitch !== "function") return;

    window.switchTab = function (name) {
      originalSwitch(name);
      const active = document.querySelector(".tab-content.active");
      if (active && !prefersReducedMotion) {
        active.classList.remove("tab-enter");
        void active.offsetWidth;
        active.classList.add("tab-enter");
      }
    };
  }

  function init() {
    document.body.classList.add("app-visible");
    initScrollReveal();
    initHeroScrollEffects();
    EmptyOrb.init();
    initTabAnimations();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.EmptyOrb = EmptyOrb;
})();
