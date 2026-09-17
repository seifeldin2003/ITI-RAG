// --- Interactive Fluid Canvas: Push & Catch Physics (Turquoise, Liquid Gold, Orange) ---
(function() {
  const canvas = document.getElementById('bg-canvas');
  if (!canvas) return;
  const gl = canvas.getContext('webgl');
  if (!gl) return;

  const vsSource = `
    attribute vec4 aVertexPosition;
    varying vec2 v_texCoord;
    void main() {
      gl_Position = aVertexPosition;
      v_texCoord = aVertexPosition.xy * 0.5 + 0.5;
    }
  `;

  // Palette: Turquoise, Liquid Gold & Orange with Push & Catch Physics
  const fsSource = `
    precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    uniform vec2 u_mouse;
    uniform float u_mouseSpeed;
    uniform float u_isCatching; // 1.0 = Catching (attracting), 0.0 = Pushing (repelling)
    uniform float u_smashTime;
    varying vec2 v_texCoord;

    float noise(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
    }

    void main() {
      vec2 uv = v_texCoord;
      vec2 p = (gl_FragCoord.xy * 2.0 - u_resolution.xy) / min(u_resolution.x, u_resolution.y);
      
      vec2 m = u_mouse / u_resolution;
      vec2 mp = (m * 2.0 - 1.0) * (u_resolution.xy / min(u_resolution.x, u_resolution.y));
      mp.y *= -1.0; 

      // Deep Obsidian base
      vec3 color = vec3(0.02, 0.024, 0.03);
      
      float n = noise(uv + u_time * 0.012);
      color += n * 0.01;
      
      // --- INTERACTIVE PUSH & CATCH PHYSICS ---
      float dMouse = length(p - mp);
      
      // Push vs Catch Interaction
      if (u_isCatching > 0.5) {
        // CATCH MODE: Gravity suction / vortex pulling energy into the cursor
        float catchRadius = smoothstep(0.8, 0.0, dMouse);
        float vortex = sin(dMouse * 18.0 - u_time * 8.0) * 0.04 * catchRadius;
        vec3 catchGlow = mix(vec3(0.96, 0.78, 0.41), vec3(0.0, 0.96, 1.0), catchRadius);
        color += catchGlow * (catchRadius * 0.35 + vortex);
      } else {
        // PUSH MODE: Fluid displacement wave pushed by cursor movement
        float pushRadius = smoothstep(0.55 + u_mouseSpeed * 0.3, 0.0, dMouse);
        float pushWave = sin(dMouse * 12.0 - u_time * 3.0) * (0.015 + u_mouseSpeed * 0.025) * pushRadius;
        
        vec3 pushAura = mix(vec3(0.0, 0.96, 1.0), vec3(0.96, 0.78, 0.41), pushRadius);
        color += pushAura * (pushWave + pushRadius * 0.04);
      }

      // Center Collision Splash & Shockwave (on submit)
      float splashActive = smoothstep(0.0, 0.35, u_smashTime) * (1.0 - smoothstep(0.9, 2.2, u_smashTime));
      
      if (splashActive > 0.0) {
        vec2 splashOrigin = vec2(0.0, -0.65); 
        float dist = length(p - splashOrigin);
        float expansion = splashActive * 4.6;
        float ring = smoothstep(expansion - 0.4, expansion, dist) * (1.0 - smoothstep(expansion, expansion + 0.4, dist));
        
        vec3 cTurquoise = vec3(0.0, 0.96, 1.0);
        vec3 cGold = vec3(0.96, 0.78, 0.41);
        vec3 cOrange = vec3(1.0, 0.36, 0.0);
        
        vec3 waveColor = mix(cTurquoise, cGold, sin(u_time * 1.5 + dist));
        waveColor = mix(waveColor, cOrange, ring * 0.3);
        
        color += waveColor * ring * splashActive * (2.0 / (dist + 0.38));
        
        float ripple = sin(dist * 22.0 - u_time * 11.0) * 0.045 * splashActive * exp(-dist * 1.5);
        color += cGold * ripple;
      }
      
      // Delicate vignette
      color *= 1.0 - length(p) * 0.32;
      
      gl_FragColor = vec4(color, 1.0);
    }
  `;

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
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

  let mouseX = window.innerWidth * 0.5, mouseY = window.innerHeight * 0.5;
  let lastX = mouseX, lastY = mouseY;
  let mouseSpeed = 0.0;
  let isCatching = 0.0;
  let smashTime = 100.0;
  let isSmashing = false;

  // Parallax reference to splash screen
  const heroSplash = document.getElementById('hero-splash');

  window.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    
    // Calculate cursor movement speed for fluid push
    const dx = mouseX - lastX;
    const dy = mouseY - lastY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    mouseSpeed = Math.min(dist / 25.0, 1.0);
    lastX = mouseX;
    lastY = mouseY;

    // Gentle parallax float on splash screen elements
    if (heroSplash && heroSplash.style.display !== 'none') {
      const offsetX = (mouseX / window.innerWidth - 0.5) * 16;
      const offsetY = (mouseY / window.innerHeight - 0.5) * 14;
      heroSplash.style.transform = `translate3d(${offsetX}px, ${offsetY}px, 0)`;
    }
  });

  // USER REQUIREMENT: Click / hold to CATCH liquid energy
  window.addEventListener('mousedown', () => {
    isCatching = 1.0;
  });

  window.addEventListener('mouseup', () => {
    isCatching = 0.0;
  });

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function renderWebGL(time) {
    time *= 0.001;
    
    // Smooth decay for mouse speed
    mouseSpeed *= 0.92;

    if (isSmashing) {
      smashTime += 0.016;
      if (smashTime > 3.0) isSmashing = false;
    }

    gl.uniform1f(uTimeLocation, time);
    gl.uniform2f(uResolutionLocation, canvas.width, canvas.height);
    gl.uniform2f(uMouseLocation, mouseX, mouseY);
    gl.uniform1f(uMouseSpeedLocation, mouseSpeed);
    gl.uniform1f(uIsCatchingLocation, isCatching);
    gl.uniform1f(uSmashTimeLocation, smashTime);

    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    requestAnimationFrame(renderWebGL);
  }
  requestAnimationFrame(renderWebGL);
  
  // Public trigger for center splash shockwave
  window.triggerSmashWebGL = function() {
    smashTime = 0.0;
    isSmashing = true;
  };
})();
