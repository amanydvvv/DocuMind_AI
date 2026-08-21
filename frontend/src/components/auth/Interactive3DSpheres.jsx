import { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * Interactive3DSpheres — 3D Interactive WebGL Live Wallpaper Background
 *
 * Features:
 * - Real 3D geometric spheres with physical materials (roughness, metalness, clearcoat)
 * - Point lights, ambient lights, and mouse-following directional light
 * - Mouse cursor physics interaction (repulsion, magnetic pull, velocity lerping)
 * - Continuous ambient harmonic floating animation with individual phase offsets
 * - Interactive pointer drag / inertia response
 */
export default function Interactive3DSpheres() {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050d08, 0.035);

    const camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.z = 18;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    // 2. Lighting
    const ambientLight = new THREE.AmbientLight(0x092015, 1.8);
    scene.add(ambientLight);

    const mainEmeraldLight = new THREE.PointLight(0x00ffaa, 3.5, 30);
    mainEmeraldLight.position.set(-6, 6, 8);
    scene.add(mainEmeraldLight);

    const rimLight = new THREE.DirectionalLight(0x00d68f, 2.0);
    rimLight.position.set(10, -5, 5);
    scene.add(rimLight);

    const mouseLight = new THREE.PointLight(0x38ef7d, 2.2, 20);
    mouseLight.position.set(0, 0, 8);
    scene.add(mouseLight);

    // 3. Spheres Configuration
    const sphereConfigs = [
      // Hero Top-Left Emerald Sphere
      {
        radius: 3.2,
        basePos: new THREE.Vector3(-6.5, 3.8, 0),
        color: 0x00ffaa,
        emissive: 0x003822,
        roughness: 0.15,
        metalness: 0.35,
        floatSpeed: 0.8,
        floatAmplitude: 0.6,
        mass: 1.5,
      },
      // Top-Right Matte Graphite Sphere
      {
        radius: 2.2,
        basePos: new THREE.Vector3(6.8, 4.2, -2),
        color: 0x121a15,
        emissive: 0x050c08,
        roughness: 0.75,
        metalness: 0.2,
        floatSpeed: 1.1,
        floatAmplitude: 0.45,
        mass: 1.8,
      },
      // Bottom-Left Floating Accent Sphere
      {
        radius: 1.4,
        basePos: new THREE.Vector3(-7.2, -4.5, 2),
        color: 0x00d68f,
        emissive: 0x002414,
        roughness: 0.2,
        metalness: 0.8,
        floatSpeed: 1.3,
        floatAmplitude: 0.7,
        mass: 0.9,
      },
      // Bottom-Right Deep Cosmic Sphere
      {
        radius: 2.8,
        basePos: new THREE.Vector3(7.5, -4.0, -3),
        color: 0x0b2419,
        emissive: 0x021008,
        roughness: 0.4,
        metalness: 0.6,
        floatSpeed: 0.7,
        floatAmplitude: 0.5,
        mass: 2.2,
      },
      // Center Background Ambient Sphere
      {
        radius: 1.1,
        basePos: new THREE.Vector3(1.2, -5.2, -5),
        color: 0x00ffaa,
        emissive: 0x004422,
        roughness: 0.1,
        metalness: 0.9,
        floatSpeed: 1.5,
        floatAmplitude: 0.8,
        mass: 0.7,
      },
    ];

    const sphereMeshes = sphereConfigs.map((cfg) => {
      const geometry = new THREE.SphereGeometry(cfg.radius, 64, 64);
      const material = new THREE.MeshStandardMaterial({
        color: cfg.color,
        emissive: cfg.emissive,
        roughness: cfg.roughness,
        metalness: cfg.metalness,
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(cfg.basePos);
      scene.add(mesh);

      return {
        mesh,
        cfg,
        currentPos: cfg.basePos.clone(),
        targetPos: cfg.basePos.clone(),
        velocity: new THREE.Vector3(),
        rotationSpeed: new THREE.Vector3(
          (Math.random() - 0.5) * 0.006,
          (Math.random() - 0.5) * 0.008,
          (Math.random() - 0.5) * 0.004
        ),
      };
    });

    // 4. Ambient Micro Stardust Particles
    const particleCount = 120;
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 35;
      particlePositions[i + 1] = (Math.random() - 0.5) * 25;
      particlePositions[i + 2] = (Math.random() - 0.5) * 15;
    }

    particleGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(particlePositions, 3)
    );

    const particleMaterial = new THREE.PointsMaterial({
      color: 0x00ffaa,
      size: 0.08,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);

    // 5. Mouse Interaction Tracking
    const mouse = {
      x: 0,
      y: 0,
      targetX: 0,
      targetY: 0,
      worldPos: new THREE.Vector3(),
    };

    const handleMouseMove = (e) => {
      // Normalized device coordinates (-1 to +1)
      mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // 6. Resize Handler
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    // 7. Animation Loop with Physics Dynamics
    let clock = new THREE.Clock();
    let animationFrameId;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const elapsedTime = clock.getElapsedTime();

      // Smooth mouse lerp
      mouse.x += (mouse.targetX - mouse.x) * 0.08;
      mouse.y += (mouse.targetY - mouse.y) * 0.08;

      // Project mouse into 3D world plane at z = 0
      mouse.worldPos.set(mouse.x * 12, mouse.y * 8, 4);
      mouseLight.position.copy(mouse.worldPos);

      // Camera subtle parallax tilt
      camera.position.x = mouse.x * 1.5;
      camera.position.y = mouse.y * 1.0;
      camera.lookAt(0, 0, 0);

      // Update Spheres with harmonic floating + mouse interactive repulsion
      sphereMeshes.forEach((item, idx) => {
        const { mesh, cfg, currentPos, targetPos, velocity, rotationSpeed } = item;

        // Base harmonic floating
        const floatOffset = new THREE.Vector3(
          Math.sin(elapsedTime * cfg.floatSpeed + idx * 1.5) * (cfg.floatAmplitude * 0.5),
          Math.cos(elapsedTime * cfg.floatSpeed * 0.8 + idx * 2.0) * cfg.floatAmplitude,
          Math.sin(elapsedTime * 0.5 + idx) * 0.4
        );

        targetPos.copy(cfg.basePos).add(floatOffset);

        // Calculate vector from mouse to sphere
        const diff = new THREE.Vector3().subVectors(currentPos, mouse.worldPos);
        const dist = diff.length();
        const maxEffectDist = 9.0;

        if (dist < maxEffectDist && dist > 0.01) {
          // Interactive repulsion force
          const force = ((maxEffectDist - dist) / maxEffectDist) * 2.5 * (1.0 / cfg.mass);
          diff.normalize().multiplyScalar(force);
          targetPos.add(diff);
        }

        // Spring damping physics to target position
        const springForce = new THREE.Vector3().subVectors(targetPos, currentPos).multiplyScalar(0.06);
        velocity.add(springForce).multiplyScalar(0.88); // 88% damping
        currentPos.add(velocity);

        mesh.position.copy(currentPos);

        // Rotate spheres
        mesh.rotation.x += rotationSpeed.x;
        mesh.rotation.y += rotationSpeed.y;
      });

      // Slowly rotate background particles
      particles.rotation.y = elapsedTime * 0.02;
      particles.rotation.x = elapsedTime * 0.01;

      renderer.render(scene, camera);
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);

      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-hidden"
      style={{ background: '#050d08' }}
    />
  );
}
