import { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * Interactive3DSpheres — Ambient Volumetric Aurora & 3D Stardust Constellation
 *
 * Clean, modern SaaS dark background:
 * - Pure volumetric emerald aurora & radial ambient lighting
 * - Interactive 3D stardust particle field with smooth cursor parallax and mouse physics
 * - No bulky 3D blocks or polygon meshes
 */
export default function Interactive3DSpheres() {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene Setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x040a06, 0.04);

    const camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.z = 16;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    // 2. High-Tech Studio Lighting
    const ambientLight = new THREE.AmbientLight(0x061a10, 2.5);
    scene.add(ambientLight);

    const topCyanLight = new THREE.PointLight(0x00ffaa, 3.5, 35);
    topCyanLight.position.set(-8, 8, 7);
    scene.add(topCyanLight);

    const emeraldRimLight = new THREE.DirectionalLight(0x00ffcc, 2.2);
    emeraldRimLight.position.set(9, -6, 6);
    scene.add(emeraldRimLight);

    const mouseLight = new THREE.PointLight(0x00ffaa, 3.2, 22);
    mouseLight.position.set(0, 0, 7);
    scene.add(mouseLight);

    // 3. Floating Luminous Stardust Particles Constellation
    const particleCount = 240;
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 42;
      particlePositions[i + 1] = (Math.random() - 0.5) * 28;
      particlePositions[i + 2] = (Math.random() - 0.5) * 20;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0x00ffaa,
      size: 0.14,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // 4. Mouse Interaction Tracking
    const mouse = {
      x: 0,
      y: 0,
      targetX: 0,
      targetY: 0,
      worldPos: new THREE.Vector3(),
    };

    const handleMouseMove = (e) => {
      mouse.targetX = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
    };
    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    // 5. Animation Loop
    let clock = new THREE.Clock();
    let animId;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth mouse lerping
      mouse.x += (mouse.targetX - mouse.x) * 0.06;
      mouse.y += (mouse.targetY - mouse.y) * 0.06;

      mouse.worldPos.set(mouse.x * 12, mouse.y * 8, 4);
      mouseLight.position.copy(mouse.worldPos);

      // Camera subtle parallax
      camera.position.x = mouse.x * 1.5;
      camera.position.y = mouse.y * 1.0;
      camera.lookAt(0, 0, 0);

      // Slowly rotate and oscillate particle field
      particles.rotation.y = elapsed * 0.018;
      particles.rotation.x = elapsed * 0.009;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);

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
      style={{
        background: 'radial-gradient(circle at 50% 35%, #0a2417 0%, #05130b 45%, #020704 100%)',
      }}
    >
      {/* Top Left Volumetric Ambient Aurora Glow */}
      <div
        className="absolute top-[5%] left-[10%] w-[450px] h-[450px] rounded-full blur-[110px] pointer-events-none opacity-45"
        style={{
          background: 'radial-gradient(circle, #00ffaa 0%, #00d68f 40%, transparent 70%)',
        }}
      />
      {/* Top Right Atmospheric Mint Aura */}
      <div
        className="absolute top-[10%] right-[10%] w-[380px] h-[380px] rounded-full blur-[100px] pointer-events-none opacity-35"
        style={{
          background: 'radial-gradient(circle, #00ffcc 0%, #008f5d 50%, transparent 70%)',
        }}
      />
      {/* Bottom Center Subtle Grounding Glow */}
      <div
        className="absolute bottom-[5%] left-[30%] w-[500px] h-[300px] rounded-full blur-[120px] pointer-events-none opacity-25"
        style={{
          background: 'radial-gradient(ellipse, #00d68f 0%, transparent 70%)',
        }}
      />
    </div>
  );
}
