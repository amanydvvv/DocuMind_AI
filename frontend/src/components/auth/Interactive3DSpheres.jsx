import { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * Interactive3DSpheres — High-End Glass Geometric Polyhedrons & Neural Constellation
 *
 * Modern luxury SaaS aesthetic (Linear / Vercel style):
 * - Refractive frosted crystal polyhedrons (Icosahedron / Octahedron / Dodecahedron)
 * - Delicate luminous emerald wireframe lattices
 * - Interactive 3D particle constellation with mouse gravity & fluid waves
 * - Smooth lerped physics and dynamic camera tilt
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
    const ambientLight = new THREE.AmbientLight(0x061a10, 2.0);
    scene.add(ambientLight);

    const topCyanLight = new THREE.PointLight(0x00ffaa, 3.0, 25);
    topCyanLight.position.set(-8, 8, 6);
    scene.add(topCyanLight);

    const emeraldRimLight = new THREE.DirectionalLight(0x00d68f, 1.8);
    emeraldRimLight.position.set(8, -6, 5);
    scene.add(emeraldRimLight);

    const mouseLight = new THREE.PointLight(0x00ffaa, 2.2, 18);
    mouseLight.position.set(0, 0, 6);
    scene.add(mouseLight);

    // 3. Glass Crystal Polyhedrons (Translucent Core + Delicate Wireframe Lattice)
    const crystalConfigs = [
      // Hero Top-Left Refractive Icosahedron
      {
        type: 'icosahedron',
        radius: 2.8,
        detail: 0,
        basePos: new THREE.Vector3(-6.8, 3.8, 1),
        coreColor: 0x072818,
        wireColor: 0x00ffaa,
        roughness: 0.1,
        metalness: 0.85,
        wireOpacity: 0.6,
        floatSpeed: 0.7,
        floatAmp: 0.5,
      },
      // Top-Right Sleek Octahedron
      {
        type: 'octahedron',
        radius: 2.2,
        detail: 0,
        basePos: new THREE.Vector3(7.2, 4.0, -1),
        coreColor: 0x0a1c14,
        wireColor: 0x00d68f,
        roughness: 0.2,
        metalness: 0.7,
        wireOpacity: 0.45,
        floatSpeed: 0.9,
        floatAmp: 0.4,
      },
      // Bottom-Left Floating Dodecahedron
      {
        type: 'dodecahedron',
        radius: 1.5,
        detail: 0,
        basePos: new THREE.Vector3(-7.5, -4.5, 2),
        coreColor: 0x052014,
        wireColor: 0x38ef7d,
        roughness: 0.15,
        metalness: 0.9,
        wireOpacity: 0.7,
        floatSpeed: 1.2,
        floatAmp: 0.6,
      },
      // Bottom-Right Background Prism
      {
        type: 'icosahedron',
        radius: 2.5,
        detail: 0,
        basePos: new THREE.Vector3(7.8, -4.2, -3),
        coreColor: 0x04160d,
        wireColor: 0x00a86b,
        roughness: 0.3,
        metalness: 0.6,
        wireOpacity: 0.35,
        floatSpeed: 0.6,
        floatAmp: 0.4,
      },
      // Center Background Floating Gem
      {
        type: 'octahedron',
        radius: 1.2,
        detail: 0,
        basePos: new THREE.Vector3(0.5, -5.5, -4),
        coreColor: 0x08331e,
        wireColor: 0x00ffaa,
        roughness: 0.05,
        metalness: 0.95,
        wireOpacity: 0.8,
        floatSpeed: 1.4,
        floatAmp: 0.7,
      },
    ];

    const crystalMeshes = crystalConfigs.map((cfg) => {
      let geo;
      if (cfg.type === 'icosahedron') geo = new THREE.IcosahedronGeometry(cfg.radius, cfg.detail);
      else if (cfg.type === 'octahedron') geo = new THREE.OctahedronGeometry(cfg.radius, cfg.detail);
      else geo = new THREE.DodecahedronGeometry(cfg.radius, cfg.detail);

      // Glass core material
      const coreMat = new THREE.MeshPhysicalMaterial({
        color: cfg.coreColor,
        roughness: cfg.roughness,
        metalness: cfg.metalness,
        clearcoat: 1.0,
        clearcoatRoughness: 0.1,
        reflectivity: 0.9,
        transmission: 0.4,
        ior: 1.5,
      });
      const coreMesh = new THREE.Mesh(geo, coreMat);

      // Delicate wireframe outline
      const wireMat = new THREE.MeshBasicMaterial({
        color: cfg.wireColor,
        wireframe: true,
        transparent: true,
        opacity: cfg.wireOpacity,
      });
      const wireMesh = new THREE.Mesh(geo, wireMat);
      wireMesh.scale.set(1.002, 1.002, 1.002);

      const group = new THREE.Group();
      group.add(coreMesh);
      group.add(wireMesh);
      group.position.copy(cfg.basePos);
      scene.add(group);

      return {
        group,
        cfg,
        currentPos: cfg.basePos.clone(),
        targetPos: cfg.basePos.clone(),
        velocity: new THREE.Vector3(),
        rotSpeed: new THREE.Vector3(
          (Math.random() - 0.5) * 0.008,
          (Math.random() - 0.5) * 0.012,
          (Math.random() - 0.5) * 0.006
        ),
      };
    });

    // 4. Floating Neural Constellation Lines & Points
    const particleCount = 140;
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 36;
      particlePositions[i + 1] = (Math.random() - 0.5) * 24;
      particlePositions[i + 2] = (Math.random() - 0.5) * 16;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0x00ffaa,
      size: 0.07,
      transparent: true,
      opacity: 0.5,
      blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
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

    // 6. Animation Loop
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
      camera.position.x = mouse.x * 1.8;
      camera.position.y = mouse.y * 1.2;
      camera.lookAt(0, 0, 0);

      // Update Crystals
      crystalMeshes.forEach((item, idx) => {
        const { group, cfg, currentPos, targetPos, velocity, rotSpeed } = item;

        // Fluid harmonic float
        const floatOffset = new THREE.Vector3(
          Math.sin(elapsed * cfg.floatSpeed + idx * 1.3) * (cfg.floatAmp * 0.5),
          Math.cos(elapsed * cfg.floatSpeed * 0.9 + idx * 1.8) * cfg.floatAmp,
          Math.sin(elapsed * 0.6 + idx) * 0.3
        );

        targetPos.copy(cfg.basePos).add(floatOffset);

        // Magnetic mouse repulsion
        const diff = new THREE.Vector3().subVectors(currentPos, mouse.worldPos);
        const dist = diff.length();
        const maxDist = 8.5;

        if (dist < maxDist && dist > 0.01) {
          const force = ((maxDist - dist) / maxDist) * 2.2;
          diff.normalize().multiplyScalar(force);
          targetPos.add(diff);
        }

        // Spring damping physics
        const spring = new THREE.Vector3().subVectors(targetPos, currentPos).multiplyScalar(0.07);
        velocity.add(spring).multiplyScalar(0.86);
        currentPos.add(velocity);

        group.position.copy(currentPos);
        group.rotation.x += rotSpeed.x;
        group.rotation.y += rotSpeed.y;
        group.rotation.z += rotSpeed.z;
      });

      // Slowly rotate particle field
      particles.rotation.y = elapsed * 0.015;
      particles.rotation.x = elapsed * 0.008;

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
        background: 'radial-gradient(circle at 50% 30%, #071910 0%, #040d08 60%, #020704 100%)',
      }}
    />
  );
}
