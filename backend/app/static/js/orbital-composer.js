// --- Three.js Kinetic Orbitals with Push & Catch Cursor Interaction ---
(function() {
  const container = document.getElementById('threejs-container');
  if (!container || typeof THREE === 'undefined') return;

  const width = container.clientWidth || window.innerWidth;
  const height = container.clientHeight || 260;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(65, width / height, 0.1, 1000);
  camera.position.z = 5.0;
  camera.position.y = 0.35;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const group = new THREE.Group();
  scene.add(group);

  const createPath = (radius, thickness, color, speed, direction, opacity) => {
    const geometry = new THREE.TorusGeometry(radius, thickness, 8, 120);
    const material = new THREE.MeshBasicMaterial({ 
      color: color, 
      transparent: true, 
      opacity: opacity 
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = Math.PI * 0.52;
    group.add(mesh);
    return { mesh, speed, direction };
  };

  // Palette: Turquoise, Liquid Gold, and Burnt Orange
  const paths = [
    createPath(2.45, 0.005, 0x00F5FF, 0.005, 1, 0.45),
    createPath(2.30, 0.004, 0xF5C869, 0.008, -1, 0.4),
    createPath(2.60, 0.003, 0xFF5C00, 0.01, 1, 0.25)
  ];

  const particles = [];
  const particleColors = [0x00F5FF, 0xF5C869, 0xFF5C00, 0xF5C869];

  for (let i = 0; i < 24; i++) {
    const geo = new THREE.SphereGeometry(0.02 + Math.random() * 0.02, 8, 8);
    const color = particleColors[i % particleColors.length];
    const mat = new THREE.MeshBasicMaterial({ 
      color: color,
      transparent: true,
      opacity: 0.8
    });
    const mesh = new THREE.Mesh(geo, mat);
    scene.add(mesh);
    particles.push({
      mesh,
      angle: (i / 24) * Math.PI * 2,
      radius: 2.35 + (Math.random() - 0.5) * 0.25,
      speed: 0.01 + Math.random() * 0.016,
      baseY: (Math.random() - 0.5) * 0.25
    });
  }
  
  let collisionTime = 100.0;
  let mouseXNormalized = 0;
  let mouseYNormalized = 0;
  let isCatching = false;

  window.addEventListener('mousemove', (e) => {
    mouseXNormalized = (e.clientX / window.innerWidth - 0.5) * 2;
    mouseYNormalized = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  window.addEventListener('mousedown', () => { isCatching = true; });
  window.addEventListener('mouseup', () => { isCatching = false; });

  function animate() {
    requestAnimationFrame(animate);
    collisionTime += 0.016;
    
    const isColliding = (collisionTime < 1.4);
    
    // Group 3D tilt following cursor position
    group.rotation.y = THREE.MathUtils.lerp(group.rotation.y, mouseXNormalized * 0.35, 0.06);
    group.rotation.x = THREE.MathUtils.lerp(group.rotation.x, mouseYNormalized * 0.15, 0.06);

    paths.forEach((p, i) => {
      p.mesh.rotation.z += p.speed * p.direction;
      if (isColliding) {
        p.mesh.scale.setScalar(THREE.MathUtils.lerp(p.mesh.scale.x, 3.0, 0.12));
        p.mesh.material.opacity = THREE.MathUtils.lerp(p.mesh.material.opacity, 0.0, 0.18);
      } else {
        p.mesh.scale.setScalar(THREE.MathUtils.lerp(p.mesh.scale.x, 1.0, 0.06));
        p.mesh.material.opacity = THREE.MathUtils.lerp(p.mesh.material.opacity, 0.45 - (i * 0.08), 0.06);
      }
    });

    particles.forEach((pt) => {
      pt.angle += isCatching ? pt.speed * 2.5 : pt.speed;
      let currentRadius = pt.radius;

      if (isColliding) {
        currentRadius = pt.radius * 2.0;
      } else if (isCatching) {
        currentRadius = THREE.MathUtils.lerp(pt.radius, 1.2, 0.3); // Pull inward (catch)
      }

      pt.mesh.position.x = Math.cos(pt.angle) * currentRadius;
      pt.mesh.position.z = Math.sin(pt.angle) * currentRadius;
      pt.mesh.position.y = pt.baseY + Math.sin(pt.angle * 2.0) * 0.1;

      if (isColliding) {
        pt.mesh.scale.setScalar(THREE.MathUtils.lerp(pt.mesh.scale.x, 1.8, 0.2));
        pt.mesh.material.opacity = THREE.MathUtils.lerp(pt.mesh.material.opacity, 0.0, 0.15);
      } else {
        pt.mesh.scale.setScalar(THREE.MathUtils.lerp(pt.mesh.scale.x, isCatching ? 1.4 : 1.0, 0.08));
        pt.mesh.material.opacity = THREE.MathUtils.lerp(pt.mesh.material.opacity, 0.75, 0.08);
      }
    });

    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener('resize', () => {
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || 260;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  });
  
  window.triggerSmashThreeJS = function() {
    collisionTime = 0.0;
  };
})();
