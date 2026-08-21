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

    // 2. High-Tech Studio Lighting with Luminous Glow
    const ambientLight = new THREE.AmbientLight(0x061a10, 2.5);
    scene.add(ambientLight);

    const topCyanLight = new THREE.PointLight(0x00ffaa, 4.8, 35);
    topCyanLight.position.set(-8, 8, 7);
    scene.add(topCyanLight);

    const emeraldRimLight = new THREE.DirectionalLight(0x00ffcc, 2.8);
    emeraldRimLight.position.set(9, -6, 6);
    scene.add(emeraldRimLight);

    const mouseLight = new THREE.PointLight(0x00ffaa, 4.0, 22);
    mouseLight.position.set(0, 0, 7);
    scene.add(mouseLight);

    // 3. Glowing Glass Crystal Polyhedrons (Luminous Inner Core + Glowing Neon Lattice)
    const crystalConfigs = [
      // Hero Top-Left Refractive Glowing Icosahedron
      {
        type: 'icosahedron',
        radius: 3.0,
        detail: 0,
        basePos: new THREE.Vector3(-6.8, 3.8, 1),
        coreColor: 0x0a3822,
        emissiveColor: 0x00ffaa,
        emissiveIntensity: 0.45,
        wireColor: 0x00ffaa,
        roughness: 0.1,
        metalness: 0.85,
        wireOpacity: 0.9,
        floatSpeed: 0.7,
        floatAmp: 0.5,
      },
      // Top-Right Sleek Glowing Octahedron
      {
        type: 'octahedron',
        radius: 2.3,
        detail: 0,
        basePos: new THREE.Vector3(7.2, 4.0, -1),
        coreColor: 0x0d281c,
        emissiveColor: 0x00d68f,
        emissiveIntensity: 0.35,
        wireColor: 0x00ffcc,
        roughness: 0.15,
        metalness: 0.8,
        wireOpacity: 0.85,
        floatSpeed: 0.9,
        floatAmp: 0.4,
      },
      // Bottom-Left Floating Glowing Dodecahedron
      {
        type: 'dodecahedron',
        radius: 1.6,
        detail: 0,
        basePos: new THREE.Vector3(-7.5, -4.5, 2),
        coreColor: 0x082e1c,
        emissiveColor: 0x38ef7d,
        emissiveIntensity: 0.5,
        wireColor: 0x38ef7d,
        roughness: 0.1,
        metalness: 0.9,
        wireOpacity: 0.95,
        floatSpeed: 1.2,
        floatAmp: 0.6,
      },
      // Bottom-Right Glowing Background Prism
      {
        type: 'icosahedron',
        radius: 2.6,
        detail: 0,
        basePos: new THREE.Vector3(7.8, -4.2, -3),
        coreColor: 0x062014,
        emissiveColor: 0x00ffaa,
        emissiveIntensity: 0.3,
        wireColor: 0x00d68f,
        roughness: 0.2,
        metalness: 0.7,
        wireOpacity: 0.75,
        floatSpeed: 0.6,
        floatAmp: 0.4,
      },
      // Center Background Floating Gem
      {
        type: 'octahedron',
        radius: 1.3,
        detail: 0,
        basePos: new THREE.Vector3(0.5, -5.5, -4),
        coreColor: 0x0a4026,
        emissiveColor: 0x00ffaa,
        emissiveIntensity: 0.6,
        wireColor: 0x00ffaa,
        roughness: 0.05,
        metalness: 0.95,
        wireOpacity: 1.0,
        floatSpeed: 1.4,
        floatAmp: 0.7,
      },
    ];

    const crystalMeshes = crystalConfigs.map((cfg) => {
      let geo;
      if (cfg.type === 'icosahedron') geo = new THREE.IcosahedronGeometry(cfg.radius, cfg.detail);
      else if (cfg.type === 'octahedron') geo = new THREE.OctahedronGeometry(cfg.radius, cfg.detail);
      else geo = new THREE.DodecahedronGeometry(cfg.radius, cfg.detail);

      // Glass core material with emissive glowing interior
      const coreMat = new THREE.MeshPhysicalMaterial({
        color: cfg.coreColor,
        emissive: cfg.emissiveColor,
        emissiveIntensity: cfg.emissiveIntensity,
        roughness: cfg.roughness,
        metalness: cfg.metalness,
        clearcoat: 1.0,
        clearcoatRoughness: 0.1,
        reflectivity: 1.0,
        transmission: 0.3,
        ior: 1.6,
      });
      const coreMesh = new THREE.Mesh(geo, coreMat);

      // Luminous neon wireframe outline
      const wireMat = new THREE.MeshBasicMaterial({
        color: cfg.wireColor,
        wireframe: true,
        transparent: true,
        opacity: cfg.wireOpacity,
      });
      const wireMesh = new THREE.Mesh(geo, wireMat);
      wireMesh.scale.set(1.004, 1.004, 1.004);

      // Inner glowing point light for volumetric aura
      const innerGlow = new THREE.PointLight(cfg.emissiveColor, 2.0, cfg.radius * 3.5);
      innerGlow.position.set(0, 0, 0);

      const group = new THREE.Group();
      group.add(coreMesh);
      group.add(wireMesh);
      group.add(innerGlow);
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

    // 4. Floating Glowing Neural Constellation Particles
    const particleCount = 180;
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 38;
      particlePositions[i + 1] = (Math.random() - 0.5) * 26;
      particlePositions[i + 2] = (Math.random() - 0.5) * 18;
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0x00ffaa,
      size: 0.12,
      transparent: true,
      opacity: 0.75,
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
