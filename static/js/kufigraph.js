/* ==========================================================
   initGeoPattern(): Enhanced Islamic geometric lattice
   - Draws animated star/polygon tiles across entire page
   - Smooth progressive drawing with particle effects
   - No HTML changes needed: adds <canvas> automatically
   ========================================================== */
function initGeoPattern(){
  console.log('initGeoPattern: Enhanced version loading...');

  // Create wrapper and canvas if they don't exist
  let wrap = document.querySelector('.bg-canvas-wrap');
  if(!wrap){
    wrap = document.createElement('div');
    wrap.className = 'bg-canvas-wrap';
    const c = document.createElement('canvas');
    c.id = 'bg-canvas';
    wrap.appendChild(c);
    document.body.prepend(wrap);
  }
  const canvas = document.getElementById('bg-canvas');
  if(!canvas) return false;

  // Force wrapper & canvas to cover viewport
  wrap.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:0;';
  canvas.style.cssText = 'width:100%;height:100%;display:block;';

  const ctx = canvas.getContext('2d', { alpha: false });
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Settings
  const TILE = 160;            // Tile size
  const LINE_W = 2;            // Line thickness
  const SPEED = 150;          // Drawing speed (pixels/second)
  const GLOW_INTENSITY = 0.3;  // Glow effect strength
  const PARTICLE_COUNT = 50;   // Number of ambient particles

  // Get CSS variables
  const cssVar = (n, fb) => (getComputedStyle(document.documentElement).getPropertyValue(n).trim() || fb);

  let W=0, H=0, cols=0, rows=0, segments=[], totalLen=0;
  let particles = [];

  // Particle system for ambient effect
  class Particle {
    constructor() {
      this.reset();
    }
    
    reset() {
      this.x = Math.random() * W;
      this.y = Math.random() * H;
      this.vx = (Math.random() - 0.5) * 0.3;
      this.vy = (Math.random() - 0.5) * 0.3;
      this.life = Math.random();
      this.maxLife = 2 + Math.random() * 3;
      this.size = 1 + Math.random() * 2;
    }
    
    update(dt) {
      this.x += this.vx;
      this.y += this.vy;
      this.life += dt;
      
      if(this.life > this.maxLife || this.x < -10 || this.x > W+10 || this.y < -10 || this.y > H+10) {
        this.reset();
      }
    }
    
    draw(ctx, color) {
      const alpha = Math.sin((this.life / this.maxLife) * Math.PI) * 0.3;
      ctx.fillStyle = color.replace('rgb', 'rgba').replace(')', `, ${alpha})`);
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // Generate tile geometry with variations
  function tileSegments(x0, y0, s){
    const pts = (ax, ay) => ({ x: x0 + ax * s, y: y0 + ay * s });
    const lines = [];

    // Random variations for organic feel
    const randomScale = 0.92 + Math.random() * 0.16;
    const randomRotation = Math.random() * Math.PI / 12;
    const wobble = () => (Math.random() - 0.5) * 0.015 * s;

    const C = pts(0.5, 0.5);
    const R = 0.35 * randomScale, r = 0.18 * randomScale;
    const ANG = Math.PI / 4;

    // 8-pointed star pattern
    for (let k = 0; k < 8; k++) {
      const a1 = k * ANG + randomRotation;
      const a2 = a1 + ANG / 2;
      const P1 = pts(0.5 + R * Math.cos(a1) + wobble()/s, 0.5 + R * Math.sin(a1) + wobble()/s);
      const P2 = pts(0.5 + r * Math.cos(a2) + wobble()/s, 0.5 + r * Math.sin(a2) + wobble()/s);
      const P3 = pts(0.5 + R * Math.cos(a1 + ANG), 0.5 + R * Math.sin(a1 + ANG));
      
      lines.push([C, P1], [P1, P2], [P2, P3]);
    }

    // Outer frame with subtle variations
    const frame = [
      pts(0.0, 0.25), pts(0.25, 0.0), pts(0.75, 0.0), pts(1.0, 0.25),
      pts(1.0, 0.75), pts(0.75, 1.0), pts(0.25, 1.0), pts(0.0, 0.75)
    ];
    for (let i = 0; i < 8; i++) {
      const a = frame[i], b = frame[(i + 1) % 8];
      lines.push([
        { x: a.x + wobble(), y: a.y + wobble() }, 
        { x: b.x + wobble(), y: b.y + wobble() }
      ]);
    }

    // Add connecting lines between adjacent points
    const innerRadius = 0.25 * randomScale;
    for(let k = 0; k < 4; k++) {
      const a = k * Math.PI / 2 + randomRotation;
      const P = pts(0.5 + innerRadius * Math.cos(a), 0.5 + innerRadius * Math.sin(a));
      const Q = pts(0.5 + innerRadius * Math.cos(a + Math.PI/2), 0.5 + innerRadius * Math.sin(a + Math.PI/2));
      lines.push([P, Q]);
    }

    return lines;
  }

  // Shuffle for random drawing order
  function shuffleSegments(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  }

  function build(){
    segments = []; 
    totalLen = 0;

    const pad = 2;
    cols = Math.ceil(W / TILE) + pad;
    rows = Math.ceil(H / TILE) + pad;

    const offsetX = -((cols*TILE - W)/2);
    const offsetY = -((rows*TILE - H)/2);

    // Create multiple growth centers for simultaneous drawing
    const centers = [];
    const numCenters = 8;
    for(let i = 0; i < numCenters; i++) {
      centers.push({
        x: Math.random() * W,
        y: Math.random() * H
      });
    }

    for(let iy=0; iy<rows; iy++){
      for(let ix=0; ix<cols; ix++){
        const x0 = offsetX + ix*TILE;
        const y0 = offsetY + iy*TILE;

        const lines = tileSegments(x0, y0, TILE);
        for(const [A,B] of lines){
          const len = Math.hypot(B.x - A.x, B.y - A.y);
          const midX = (A.x + B.x) / 2;
          const midY = (A.y + B.y) / 2;
          
          // Find distance to nearest growth center
          let minDist = Infinity;
          for(const center of centers) {
            const dist = Math.hypot(midX - center.x, midY - center.y);
            if(dist < minDist) minDist = dist;
          }
          
          segments.push({
            x1: A.x, y1: A.y, 
            x2: B.x, y2: B.y, 
            len,
            startDelay: REDUCED ? 0 : minDist * 0.8, // Delay based on distance from center
            progress: 0, // Individual progress tracker
            completedAt: null // Track when segment finishes drawing
          });
        }
      }
    }

    shuffleSegments(segments);
    
    // Initialize particles
    if(!REDUCED) {
      particles = [];
      for(let i=0; i<PARTICLE_COUNT; i++) {
        particles.push(new Particle());
      }
    }
  }

  function resize(){
    const cssW = Math.max(1, window.innerWidth);
    const cssH = Math.max(1, window.innerHeight);
    canvas.width  = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    canvas.style.width  = cssW + 'px';
    canvas.style.height = cssH + 'px';
    ctx.setTransform(dpr,0,0,dpr,0,0);
    W = cssW; H = cssH;
    build();
  }
  
  window.addEventListener('resize', resize);
  resize();

  // Progressive drawing with effects
  let last = performance.now();
  let globalTime = 0;
  let hue = 0;
  const FADE_OUT_DELAY = 2000; // Start fading 2 seconds after completion
  const FADE_OUT_DURATION = 6000; // Take 1 second to fade out

  function draw(now){
    const dt = Math.min(0.05, (now - last)/1000); 
    last = now;
    globalTime += dt * SPEED;
    hue = (hue + dt * 10) % 360;

    // Background with subtle gradient
    const bgColor = cssVar('--geo-bg', '#0a0a0a');
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, W, H);

    // Update and draw particles
    if(!REDUCED) {
      const lineColor = cssVar('--geo-line', '#b08a4a');
      particles.forEach(p => {
        p.update(dt);
        p.draw(ctx, lineColor);
      });
    }

    // Main geometric lines
    const stroke = cssVar('--geo-line', '#b08a4a');
    
    // Draw with glow effect
    if(GLOW_INTENSITY > 0 && !REDUCED) {
      ctx.shadowBlur = 8;
      ctx.shadowColor = stroke;
    }
    
    ctx.strokeStyle = stroke;
    ctx.lineWidth = LINE_W;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    for (const seg of segments) {
      // Each segment starts drawing after its delay
      const activeTime = Math.max(0, globalTime - seg.startDelay);
      seg.progress = Math.min(seg.len, activeTime);
      
      // Mark completion time
      if(seg.progress >= seg.len && seg.completedAt === null) {
        seg.completedAt = now;
      }
      
      // Calculate fade out for individual segments
      let fadeOut = 1;
      if(seg.completedAt !== null) {
        const timeSinceComplete = now - seg.completedAt;
        if(timeSinceComplete > FADE_OUT_DELAY) {
          const fadeProgress = (timeSinceComplete - FADE_OUT_DELAY) / FADE_OUT_DURATION;
          fadeOut = Math.max(0, 1 - fadeProgress);
          
          // Reset segment when fully faded to create new one
          if(fadeOut <= 0) {
            seg.progress = 0;
            seg.completedAt = null;
            // Give it a new random delay to create continuous variation
            seg.startDelay = globalTime + Math.random() * 500;
            continue;
          }
        }
      }
      
      if(seg.progress <= 0) continue;

      const t = seg.progress / seg.len;
      const x = seg.x1 + (seg.x2 - seg.x1) * t;
      const y = seg.y1 + (seg.y2 - seg.y1) * t;

      // Fade in effect for newly drawn segments
      const fadeIn = Math.min(1, seg.progress / 50);
      const alpha = fadeIn * fadeOut;
      
      if(!REDUCED) {
        ctx.globalAlpha = alpha * (0.7 + Math.sin(hue / 30) * 0.3);
      } else {
        ctx.globalAlpha = alpha;
      }

      ctx.beginPath();
      ctx.moveTo(seg.x1, seg.y1);
      ctx.lineTo(x, y);
      ctx.stroke();
    }

    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;

    requestAnimationFrame(draw);
  }
  
  requestAnimationFrame(draw);
  return true;
}

// Auto-run when DOM is ready
if(document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', initGeoPattern);
}else{
  initGeoPattern();
}