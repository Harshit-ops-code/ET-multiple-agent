// frontend/js/hero.js
// Creative Generative Fluid Flow Field Canvas Animation + 3D Agent Core visualizer

(function() {
  const PARTICLE_COUNT = 140;
  const FLOW_SCALE = 0.003; // Wave scale frequency
  const PARTICLE_SPEED = 0.8;
  const MOUSE_INFLUENCE = 180;

  let canvas, ctx;
  let particles = [];
  let mouse = { x: null, y: null, targetX: null, targetY: null };
  let time = 0;
  let animationFrameId;
  let heroElement;
  let heroRunning = true;

  function init() {
    heroElement = document.getElementById("hero-page");
    canvas = document.getElementById("hero-stars");
    if (!canvas) return;
    ctx = canvas.getContext("2d");

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseleave", handleMouseLeave);

    // Initialize particles
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push(createParticle());
    }

    animate();
    
    // Initialize 3D Agent Core Avatar!
    Avatar3D.init();
  }

  function createParticle() {
    return {
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      life: Math.random() * 200 + 100,
      maxLife: 300,
      speed: Math.random() * 0.8 + 0.4,
      size: Math.random() * 1.5 + 1.2,
      // Curated light mode gradient colors (Indigo to Teal)
      color: Math.random() > 0.4 ? '79, 70, 229' : '13, 148, 136'
    };
  }

  function handleMouseMove(e) {
    mouse.targetX = e.clientX;
    mouse.targetY = e.clientY;
  }

  function handleMouseLeave() {
    mouse.targetX = null;
    mouse.targetY = null;
  }

  function resizeCanvas() {
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function animate() {
    if (!heroRunning) return;
    // Semi-transparent clearing for beautiful motion blur tail sweeps
    ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    time += 0.002;

    // Smooth mouse coordinates follow
    if (mouse.targetX !== null) {
      if (mouse.x === null) {
        mouse.x = mouse.targetX;
        mouse.y = mouse.targetY;
      } else {
        mouse.x += (mouse.targetX - mouse.x) * 0.1;
        mouse.y += (mouse.targetY - mouse.y) * 0.1;
      }
    } else {
      mouse.x = null;
      mouse.y = null;
    }

    // Update and draw particles along vector flow fields
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.life--;

      // Respawn dead particles
      if (p.life <= 0 || p.x < 0 || p.x > canvas.width || p.y < 0 || p.y > canvas.height) {
        particles[i] = createParticle();
        continue;
      }

      // Generate vector flow angle using Sine/Cosine wave combinations
      let angle = Math.sin(p.x * FLOW_SCALE + time) * Math.cos(p.y * FLOW_SCALE + time) * Math.PI * 2;

      // Mouse magnet displacement
      if (mouse.x !== null && mouse.y !== null) {
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MOUSE_INFLUENCE) {
          // Push flow angles outward around cursor
          const force = (MOUSE_INFLUENCE - dist) / MOUSE_INFLUENCE;
          const pushAngle = Math.atan2(dy, dx) + Math.PI / 2; // Vortex swirl
          angle = angle * (1 - force) + pushAngle * force;
          p.x += Math.cos(pushAngle) * force * 1.2;
          p.y += Math.sin(pushAngle) * force * 1.2;
        }
      }

      // Apply vector velocities
      p.x += Math.cos(angle) * p.speed * PARTICLE_SPEED;
      p.y += Math.sin(angle) * p.speed * PARTICLE_SPEED;

      // Render glowing flow node
      const alpha = p.life < 50 ? (p.life / 50) * 0.45 : 0.45;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.color}, ${alpha})`;
      ctx.fill();
    }

    animationFrameId = requestAnimationFrame(animate);
  }

  // ── Custom Interactive 3D Geodesic Mesh Sphere Renderer ──────────────────────
  const Avatar3D = (() => {
    let canvas, ctx, animId = null;
    let width, height;
    let points = [];
    let rotationX = 0.4, rotationY = -0.6;
    let targetRotationX = 0.4, targetRotationY = -0.6;
    let scrollBoost = 0;
    let isDragging = false;
    let isRunning = true;
    let startX = 0, startY = 0;
    let time = 0;

    // Orbiting particles representing data flows
    const orbits = [];
    const rings = [
      { rx: 1.25, ry: 0.42, tilt: 0.3, speed: 0.018, color: "79, 70, 229" },
      { rx: 1.38, ry: 0.35, tilt: -0.6, speed: -0.012, color: "13, 148, 136" },
      { rx: 1.12, ry: 0.55, tilt: 1.1, speed: 0.009, color: "79, 70, 229" }
    ];
    
    function init() {
      canvas = document.getElementById("hero-3d-avatar");
      if (!canvas) return;
      ctx = canvas.getContext("2d");
      
      resize();
      window.addEventListener("resize", resize);
      
      // Generate spherical wireframe points
      points = [];
      const numLat = 13;
      const numLng = 16;
      for (let lat = 1; lat < numLat; lat++) {
        const theta = (lat / numLat) * Math.PI;
        const sinTheta = Math.sin(theta);
        const cosTheta = Math.cos(theta);
        for (let lng = 0; lng < numLng; lng++) {
          const phi = (lng / numLng) * Math.PI * 2;
          const sinPhi = Math.sin(phi);
          const cosPhi = Math.cos(phi);
          points.push({
            ox: sinTheta * cosPhi,
            oy: cosTheta,
            oz: sinTheta * sinPhi,
            x: 0, y: 0, z: 0,
            px: 0, py: 0
          });
        }
      }
      
      // Generate orbiting micro-particles
      orbits.length = 0;
      for (let i = 0; i < 22; i++) {
        orbits.push({
          angle: Math.random() * Math.PI * 2,
          speed: 0.012 + Math.random() * 0.016,
          radius: 110 + Math.random() * 35,
          tilt: (Math.random() - 0.5) * 1.4,
          size: 1 + Math.random() * 1.5,
          color: i % 2 === 0 ? "79, 70, 229" : "13, 148, 136"
        });
      }
      
      // Mouse/Touch Drag controls for rotation
      canvas.addEventListener("mousedown", (e) => {
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
      });
      
      window.addEventListener("mousemove", (e) => {
        if (!isDragging) {
          // Soft hover parallax
          const rect = canvas.getBoundingClientRect();
          const mx = e.clientX - (rect.left + rect.width / 2);
          const my = e.clientY - (rect.top + rect.height / 2);
          targetRotationY = -0.6 + (mx / rect.width) * 0.7;
          targetRotationX = 0.4 + (my / rect.height) * 0.7;
          return;
        }
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        targetRotationY += dx * 0.007;
        targetRotationX += dy * 0.007;
        startX = e.clientX;
        startY = e.clientY;
      });
      
      window.addEventListener("mouseup", () => {
        isDragging = false;
      });
      
      canvas.addEventListener("touchstart", (e) => {
        if (e.touches.length === 1) {
          isDragging = true;
          startX = e.touches[0].clientX;
          startY = e.touches[0].clientY;
        }
      }, { passive: true });
      
      window.addEventListener("touchmove", (e) => {
        if (isDragging && e.touches.length === 1) {
          const dx = e.touches[0].clientX - startX;
          const dy = e.touches[0].clientY - startY;
          targetRotationY += dx * 0.008;
          targetRotationX += dy * 0.008;
          startX = e.touches[0].clientX;
          startY = e.touches[0].clientY;
        }
      }, { passive: true });
      
      window.addEventListener("touchend", () => {
        isDragging = false;
      });
      
      animateAvatar();
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

    function setScrollProgress(p) {
      scrollBoost = p;
      if (!isDragging) {
        targetRotationY = -0.6 + p * 1.2;
        targetRotationX = 0.4 + p * 0.35;
      }
    }

    function pause() {
      isRunning = false;
      if (animId) {
        cancelAnimationFrame(animId);
        animId = null;
      }
    }

    function resume() {
      if (isRunning) return;
      isRunning = true;
      animateAvatar();
    }

    function drawRing(cx, cy, baseR, ring, cosX, sinX, cosY, sinY) {
      const steps = 48;
      const ringAngle = time * ring.speed;
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const a = (i / steps) * Math.PI * 2 + ringAngle;
        const ox = Math.cos(a) * baseR * ring.rx;
        const oz = Math.sin(a) * baseR * ring.rx * 0.85;
        const oy = Math.sin(a + ring.tilt) * baseR * ring.ry;

        const x1 = ox * cosY - oz * sinY;
        const z1 = ox * sinY + oz * cosY;
        const y2 = oy * cosX - z1 * sinX;
        const z2 = oy * sinX + z1 * cosX;

        const f = 280;
        const scale = f / (f + z2);
        const px = cx + x1 * scale;
        const py = cy + y2 * scale;

        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      const alpha = 0.14 + Math.sin(time * 2 + ring.tilt) * 0.06;
      ctx.strokeStyle = `rgba(${ring.color}, ${alpha})`;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    function drawCore(cx, cy) {
      const pulse = 1 + Math.sin(time * 2.5) * 0.1;
      const coreR = 28 * pulse;

      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR * 1.8);
      grad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
      grad.addColorStop(0.35, "rgba(79, 70, 229, 0.25)");
      grad.addColorStop(1, "rgba(79, 70, 229, 0)");
      ctx.beginPath();
      ctx.arc(cx, cy, coreR * 1.8, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(cx, cy, coreR * 0.55, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(79, 70, 229, 0.12)";
      ctx.fill();
      ctx.strokeStyle = "rgba(79, 70, 229, 0.35)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.font = "800 14px 'Plus Jakarta Sans', sans-serif";
      ctx.fillStyle = "rgba(79, 70, 229, 0.95)";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("LX", cx, cy + 1);
    }
    
    function animateAvatar() {
      if (!canvas || !ctx || !isRunning) return;
      ctx.clearRect(0, 0, width, height);

      time += 0.012 + scrollBoost * 0.008;

      // Interpolate rotation + gentle auto-spin
      if (!isDragging) {
        targetRotationY += 0.0015 + scrollBoost * 0.004;
      }
      rotationX += (targetRotationX - rotationX) * 0.12;
      rotationY += (targetRotationY - rotationY) * 0.12;
      
      const cosX = Math.cos(rotationX);
      const sinX = Math.sin(rotationX);
      const cosY = Math.cos(rotationY);
      const sinY = Math.sin(rotationY);
      
      const cx = width / 2;
      const cy = height / 2;
      const baseR = 85;

      // Energy rings behind mesh
      rings.forEach((ring) => drawRing(cx, cy, baseR, ring, cosX, sinX, cosY, sinY));

      // 1. Waving radius morphing & 3D rotation projection
      points.forEach(p => {
        // Morph radius based on 3D coordinates + time
        const rOffset = Math.sin(p.ox * 4.5 + time) * Math.cos(p.oy * 4.5 + time) * 11;
        const r = 85 + rOffset;
        
        const sx = p.ox * r;
        const sy = p.oy * r;
        const sz = p.oz * r;
        
        // Rotate Y
        let x1 = sx * cosY - sz * sinY;
        let z1 = sx * sinY + sz * cosY;
        
        // Rotate X
        let y2 = sy * cosX - z1 * sinX;
        let z2 = sy * sinX + z1 * cosX;
        
        // Simple projection (focal length = 280)
        const f = 280;
        const scale = f / (f + z2);
        
        p.x = x1;
        p.y = y2;
        p.z = z2;
        p.px = cx + x1 * scale;
        p.py = cy + y2 * scale;
        p.scale = scale;
      });
      
      // Sort points by Z-depth (painter's algorithm)
      const sortedPoints = [...points].sort((a, b) => b.z - a.z);
      
      // 2. Render connecting lines (geodesic mesh structure)
      ctx.lineWidth = 0.5;
      for (let i = 0; i < points.length; i++) {
        const p1 = points[i];
        let connects = 0;
        for (let j = i + 1; j < points.length; j++) {
          const p2 = points[j];
          const distSq = Math.pow(p1.ox - p2.ox, 2) + Math.pow(p1.oy - p2.oy, 2) + Math.pow(p1.oz - p2.oz, 2);
          if (distSq < 0.08) {
            const zAvg = (p1.z + p2.z) / 2;
            const alpha = Math.max(0, 0.12 - (zAvg / 200));
            ctx.beginPath();
            ctx.moveTo(p1.px, p1.py);
            ctx.lineTo(p2.px, p2.py);
            ctx.strokeStyle = `rgba(79, 70, 229, ${alpha})`;
            ctx.stroke();
            connects++;
            if (connects > 3) break;
          }
        }
      }
      
      // 3. Render mesh nodes
      sortedPoints.forEach(p => {
        const size = p.scale * 1.8;
        const alpha = Math.max(0.1, 0.7 - (p.z / 250));
        ctx.beginPath();
        ctx.arc(p.px, p.py, size, 0, Math.PI * 2);
        ctx.fillStyle = p.z < 0 ? `rgba(13, 148, 136, ${alpha})` : `rgba(79, 70, 229, ${alpha})`;
        ctx.fill();
      });
      
      // 4. Render orbiting micro-particles (Data streams)
      orbits.forEach(orb => {
        orb.angle += orb.speed;
        
        const ox = Math.cos(orb.angle) * orb.radius;
        const oz = Math.sin(orb.angle) * orb.radius;
        const oy = ox * Math.sin(orb.tilt);
        
        // Rotate Y
        let x1 = ox * cosY - oz * sinY;
        let z1 = ox * sinY + oz * cosY;
        
        // Rotate X
        let y2 = oy * cosX - z1 * sinX;
        let z2 = oy * sinX + z1 * cosX;
        
        const f = 280;
        const scale = f / (f + z2);
        const px = cx + x1 * scale;
        const py = cy + y2 * scale;
        
        const size = scale * orb.size;
        const alpha = Math.max(0.05, 0.8 - (z2 / 200));
        ctx.beginPath();
        ctx.arc(px, py, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${orb.color}, ${alpha})`;
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(px, py, size * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${orb.color}, ${alpha * 0.25})`;
        ctx.fill();
      });

      // 5. Agent core
      drawCore(cx, cy);

      animId = requestAnimationFrame(animateAvatar);
    }

    return { init, setScrollProgress, pause, resume };
  })();

  window.Avatar3D = Avatar3D;

  window.enterApp = function() {
    if (!heroElement) return;
    
    // Gated Entry: Check if user is logged in
    const isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
    if (!isLoggedIn) {
      if (window.openLoginModal) {
        window.openLoginModal();
      } else {
        alert("Please sign in to access the Content Engine.");
      }
      return;
    }

    heroElement.classList.add("fade-out");
    heroRunning = false;
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    Avatar3D.pause();
    setTimeout(() => {
      heroElement.style.display = "none";
      document.body.style.overflow = "";
    }, 600);
  };

  window.showHeroPage = function() {
    if (!heroElement) return;
    heroElement.style.display = "block";
    document.body.style.overflow = "hidden";
    heroRunning = true;
    void heroElement.offsetWidth;
    heroElement.classList.remove("fade-out");
    Avatar3D.resume();
    animate();
  };

  document.body.style.overflow = "hidden";

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
