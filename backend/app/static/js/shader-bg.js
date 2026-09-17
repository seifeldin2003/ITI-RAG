// --- AutoDiag Dynamic Fluid Canvas: Living Aurora & Squash Physics ---
(function() {
  const canvas = document.getElementById('bg-canvas');
  if (!canvas) return;
  const gl = canvas.getContext('webgl', { antialias: true, alpha: false });
  if (!gl) return;

  const vsSource = `
    attribute vec4 aVertexPosition;
    varying vec2 v_texCoord;
    void main() {
      gl_Position = aVertexPosition;
      v_texCoord = aVertexPosition.xy * 0.5 + 0.5;
    }
  `;

  // Palette: Obsidian Navy, Electric Turquoise (#00F5FF), Liquid Gold (#F5C869), Squash Orange (#FF5C00), Neon Magenta
  const fsSource = `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec2 u_mouse;
    uniform float u_mouseSpeed;
    uniform float u_isCatching;
    uniform float u_smashTime;
    uniform vec2 u_smashOrigin;
    varying vec2 v_texCoord;

    // Simplex/fBm style smooth noise
    vec2 hash2(vec2 p) {
      p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
      return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
    }

    float noise(vec2 p) {
      const float K1 = 0.366025404; // (sqrt(3)-1)/2;
      const float K2 = 0.211324865; // (3-sqrt(3))/6;
      vec2 i = floor(p + (p.x + p.y) * K1);
      vec2 a = p - i + (i.x + i.y) * K2;
      vec2 o = (a.x > a.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
      vec2 b = a - o + K2;
      vec2 c = a - 1.0 + 2.0 * K2;
      vec3 h = max(0.5 - vec3(dot(a,a), dot(b,b), dot(c,c)), 0.0);
      vec3 n = h*h*h*h * vec3(dot(a, hash2(i)), dot(b, hash2(i + o)), dot(c, hash2(i + 1.0)));
      return dot(n, vec3(70.0));
    }

    float fbm(vec2 p) {
      float f = 0.0;
      float w = 0.5;
      for (int i = 0; i < 3; i++) {
        f += w * noise(p);
        p *= 2.02;
        w *= 0.5;
      }
      return f;
    }

    void main() {
      vec2 uv = v_texCoord;
      vec2 p = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / min(u_resolution.x, u_resolution.y);
      
      // Normalized cursor position in aspect-corrected coordinates
      vec2 m = u_mouse / u_resolution;
      vec2 mp = (m * 2.0 - 1.0) * (u_resolution.xy / min(u_resolution.x, u_resolution.y));
      mp.y *= -1.0; 

      float dMouse = length(p - mp);

      // --- DYNAMIC CURSOR FLUID WARP ---
      // Moving cursor pushes and distorts the fluid coordinates
      vec2 mouseDir = p - mp;
      float pushStrength = exp(-dMouse * 2.4) * (0.45 + u_mouseSpeed * 0.55);
      vec2 warpedP = p + normalize(mouseDir + 0.001) * pushStrength * 0.35;

      // Continuous organic drifting fluid currents (Never static!)
      float t = u_time * 0.25;
      vec2 q = vec2(
        fbm(warpedP + vec2(t * 0.3, t * 0.2)),
        fbm(warpedP + vec2(-t * 0.2, t * 0.4))
      );

      vec2 r = vec2(
        fbm(warpedP + 4.0 * q + vec2(1.7, 9.2) + 0.15 * t),
        fbm(warpedP + 4.0 * q + vec2(8.3, 2.8) + 0.126 * t)
      );

      float f = fbm(warpedP + 3.0 * r);

      // Base Obsidian Palette with subtle deep blues and charcoal
      vec3 baseDark = vec3(0.024, 0.028, 0.038);
      vec3 cIndigo = vec3(0.035, 0.05, 0.09);
      vec3 cTurquoise = vec3(0.0, 0.96, 1.0);
      vec3 cGold = vec3(0.98, 0.78, 0.41);
      vec3 cOrange = vec3(1.0, 0.36, 0.0);
      vec3 cSquashPink = vec3(1.0, 0.15, 0.45);

      // Living Aurora background blending
      vec3 color = mix(baseDark, cIndigo, clamp(f * 1.8, 0.0, 1.0));
      color = mix(color, cTurquoise * 0.22, clamp(length(q) * 0.7, 0.0, 1.0));
      color = mix(color, cGold * 0.15, clamp(r.x * r.x * 0.8, 0.0, 1.0));
      color = mix(color, cOrange * 0.12, clamp(pow(f, 3.0) * 1.4, 0.0, 1.0));

      // --- CURSOR-FOLLOWING DYNAMIC LUMINESCENCE ---
      // Glowing aura following the cursor wherever it moves
      float cursorCore = exp(-dMouse * 3.8);
      float cursorHalo = exp(-dMouse * 1.6) * 0.42;
      float cursorRipple = sin(dMouse * 16.0 - u_time * 4.0) * exp(-dMouse * 2.2) * (0.04 + u_mouseSpeed * 0.08);

      vec3 cursorAuraColor = mix(cTurquoise, cGold, clamp(sin(u_time * 1.2) * 0.5 + 0.5, 0.0, 1.0));
      cursorAuraColor = mix(cursorAuraColor, cOrange, clamp(u_mouseSpeed * 1.4, 0.0, 1.0));

      if (u_isCatching > 0.5) {
        // CATCH / HOLD MODE: Gravitational vortex sucking energy into the pointer
        float catchRadius = smoothstep(0.9, 0.0, dMouse);
        float vortex = sin(dMouse * 22.0 - u_time * 10.0) * 0.08 * catchRadius;
        vec3 catchGlow = mix(cGold, cTurquoise, catchRadius);
        color += catchGlow * (catchRadius * 0.6 + vortex);
      } else {
        // PUSH MODE: Fluid displacement & luminous wake following the cursor
        color += cursorAuraColor * (cursorCore * 0.65 + cursorHalo + cursorRipple);
      }

      // --- SQUASH COLLISION & SHOCKWAVE (WHEN DIAGNOSE IS CLICKED) ---
      if (u_smashTime < 2.5) {
        float st = u_smashTime;
        vec2 origin = u_smashOrigin;
        float distToOrigin = length(p - origin);

        // Multiple expanding chromatic shockwave rings
        float ringSpeed1 = st * 3.8;
        float ring1 = smoothstep(ringSpeed1 - 0.25, ringSpeed1, distToOrigin) * (1.0 - smoothstep(ringSpeed1, ringSpeed1 + 0.25, distToOrigin));

        float ringSpeed2 = max(0.0, (st - 0.12) * 4.4);
        float ring2 = smoothstep(ringSpeed2 - 0.35, ringSpeed2, distToOrigin) * (1.0 - smoothstep(ringSpeed2, ringSpeed2 + 0.35, distToOrigin));

        float ringSpeed3 = max(0.0, (st - 0.25) * 5.0);
        float ring3 = smoothstep(ringSpeed3 - 0.45, ringSpeed3, distToOrigin) * (1.0 - smoothstep(ringSpeed3, ringSpeed3 + 0.45, distToOrigin));

        float fade = exp(-st * 1.6);

        // Vibrant squash colors explosion
        vec3 blastTurquoise = cTurquoise * 1.5;
        vec3 blastGold = cGold * 1.6;
        vec3 blastOrange = cOrange * 1.8;
        vec3 blastPink = cSquashPink * 1.4;

        color += blastTurquoise * ring1 * fade * 1.3;
        color += blastGold * ring2 * fade * 1.2;
        color += blastOrange * ring3 * fade * 1.1;

        // Radial dispersion wave
        float centerGlow = exp(-distToOrigin * 2.0) * fade * 0.7;
        color += mix(blastGold, blastPink, sin(st * 6.0) * 0.5 + 0.5) * centerGlow;

        // Concentric ripples across entire screen
        float fluidRipple = sin(distToOrigin * 24.0 - st * 14.0) * 0.08 * fade * exp(-distToOrigin * 0.8);
        color += mix(cTurquoise, cOrange, 0.5 + 0.5 * sin(st * 4.0)) * fluidRipple;
      }

      // Gentle luxury vignette
      color *= 1.0 - length(p) * 0.25;

      gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
    }
  `;

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error(gl.getShaderInfoLog(shader));
    }
    return shader;
  }

  const shaderProgram = gl.createProgram();
  gl.attachShader(shaderProgram, compileShader(gl, gl.VERTEX_SHADER, vsSource));
  gl.attachShader(shaderProgram, compileShader(gl, gl.FRAGMENT_SHADER, fsSource));
  gl.linkProgram(shaderProgram);
  gl.useProgram(shaderProgram);

  const positions = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
  const positionBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

  const positionLocation = gl.getAttribLocation(shaderProgram, 'aVertexPosition');
  gl.enableVertexAttribArray(positionLocation);
  gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

  const uTimeLocation = gl.getUniformLocation(shaderProgram, 'u_time');
  const uResolutionLocation = gl.getUniformLocation(shaderProgram, 'u_resolution');
  const uMouseLocation = gl.getUniformLocation(shaderProgram, 'u_mouse');
  const uMouseSpeedLocation = gl.getUniformLocation(shaderProgram, 'u_mouseSpeed');
  const uIsCatchingLocation = gl.getUniformLocation(shaderProgram, 'u_isCatching');
  const uSmashTimeLocation = gl.getUniformLocation(shaderProgram, 'u_smashTime');
  const uSmashOriginLocation = gl.getUniformLocation(shaderProgram, 'u_smashOrigin');

  let targetX = window.innerWidth * 0.5;
  let targetY = window.innerHeight * 0.5;
  let currentX = targetX;
  let currentY = targetY;
  let lastX = currentX;
  let lastY = currentY;
  let mouseSpeed = 0.0;
  let isCatching = 0.0;
  let smashTime = 100.0;
  let isSmashing = false;
  let smashOriginX = 0.0;
  let smashOriginY = -0.65;

  const heroSplash = document.getElementById('hero-splash');
  const atmosphericOverlay = document.querySelector('.atmospheric-overlay');

  window.addEventListener('mousemove', (e) => {
    targetX = e.clientX;
    targetY = e.clientY;
    
    // Parallax float on splash elements
    if (heroSplash && heroSplash.style.display !== 'none') {
      const offsetX = (targetX / window.innerWidth - 0.5) * 22;
      const offsetY = (targetY / window.innerHeight - 0.5) * 18;
      heroSplash.style.transform = `translate3d(${offsetX}px, ${offsetY}px, 0)`;
    }

    // Dynamic subtle drift on atmospheric lighting
    if (atmosphericOverlay) {
      const pctX = Math.round((targetX / window.innerWidth) * 100);
      const pctY = Math.round((targetY / window.innerHeight) * 100);
      atmosphericOverlay.style.background = `
        radial-gradient(circle at ${pctX}% ${pctY}%, rgba(0,245,255,0.12) 0%, transparent 42%),
        radial-gradient(circle at ${100 - pctX}% ${100 - pctY}%, rgba(245,200,105,0.08) 0%, transparent 48%),
        radial-gradient(circle at 50% 95%, rgba(255,92,0,0.06) 0%, transparent 45%),
        linear-gradient(to bottom, rgba(5,6,8,0.2) 0%, rgba(5,6,8,0.6) 70%, rgba(5,6,8,0.95) 100%)
      `;
    }
  });

  window.addEventListener('mousedown', () => { isCatching = 1.0; });
  window.addEventListener('mouseup', () => { isCatching = 0.0; });

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function renderWebGL(time) {
    time *= 0.001;
    
    // Smooth trailing physics for cursor
    currentX += (targetX - currentX) * 0.14;
    currentY += (targetY - currentY) * 0.14;

    const dx = currentX - lastX;
    const dy = currentY - lastY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    mouseSpeed = Math.min(dist / 14.0, 1.0);
    lastX = currentX;
    lastY = currentY;

    if (isSmashing) {
      smashTime += 0.016;
      if (smashTime > 2.8) isSmashing = false;
    }

    gl.uniform1f(uTimeLocation, time);
    gl.uniform2f(uResolutionLocation, canvas.width, canvas.height);
    gl.uniform2f(uMouseLocation, currentX, currentY);
    gl.uniform1f(uMouseSpeedLocation, mouseSpeed);
    gl.uniform1f(uIsCatchingLocation, isCatching);
    gl.uniform1f(uSmashTimeLocation, smashTime);
    gl.uniform2f(uSmashOriginLocation, smashOriginX, smashOriginY);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    requestAnimationFrame(renderWebGL);
  }
  requestAnimationFrame(renderWebGL);
  
  // Public trigger for squash color shockwave
  window.triggerSmashWebGL = function(customOriginX, customOriginY) {
    if (typeof customOriginX === 'number' && typeof customOriginY === 'number') {
      const minDim = Math.min(canvas.width, canvas.height);
      smashOriginX = (customOriginX * 2.0 - canvas.width) / minDim;
      smashOriginY = -((customOriginY * 2.0 - canvas.height) / minDim);
    } else {
      smashOriginX = 0.0;
      smashOriginY = -0.65;
    }
    smashTime = 0.0;
    isSmashing = true;
  };
})();
