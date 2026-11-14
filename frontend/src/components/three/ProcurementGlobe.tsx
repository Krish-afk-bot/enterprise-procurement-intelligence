import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { useMotionMode } from "@/motion/motion";
import { EARTH_LAND_NODES, LandNode } from "./earthLandNodes";

/* ==========================================================================
   TWEAKABLE CONSTANTS (EPI Document Knowledge Graph)
   ========================================================================== */
export const GLOBE_CONFIG = {
  BASE_RADIUS: 100, // Normalized world radius, scaled dynamically by ResizeObserver
  CONTAINER_PADDING: 64, // Generous px padding from container edges (zero clipping)

  // 6 Continental Clusters mapped to real Enterprise Procurement Entity Types
  CLUSTERS: [
    { type: "Master Service Agreements & Contracts", region: "North America", baseColor: 0xff4d00 },
    { type: "Invoices & Billing Schedules", region: "South America", baseColor: 0xff5a12 },
    { type: "Supplier & Entity Records", region: "Europe", baseColor: 0xeb4800 },
    { type: "Procurement Policies & Standards", region: "Africa", baseColor: 0xf55200 },
    { type: "Compliance & Trade Filings", region: "Asia", baseColor: 0xff6b22 },
    { type: "Independent Audit & Verification Reports", region: "Oceania", baseColor: 0xff7733 },
  ],

  // Node sizes (pixels in Orthographic projection)
  MIN_NODE_SIZE: 0.9,
  MAX_NODE_SIZE: 1.4,
  HUB_NODE_SIZE: 2.1,
  HUB_COUNT: 16,

  // Edges
  NEAREST_NEIGHBORS: 3,
  OCEAN_ARCS_COUNT: 22,
  EDGE_OPACITY: 0.20,
  ARC_OPACITY: 0.22,
  RIM_OPACITY: 0.20,

  // Water & Depth (back-half dimming to ~25% visibility)
  WATER_COLOR: 0x0d0805,
  WATER_OPACITY: 0.75,

  // Animation
  ROTATION_SPEED_Y: 0.0016,
  ROTATION_SPEED_X: 0.0003,
  PULSE_SPEED: 0.012,
  ACTIVE_PULSES_COUNT: 4,
  HIGHLIGHT_INTERVAL_TICKS: 220,
};

interface HoveredNodeInfo {
  title: string;
  type: string;
  region: string;
  x: number;
  y: number;
}

export function ProcurementGlobe({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<HoveredNodeInfo | null>(null);
  const [webglSupported, setWebglSupported] = useState(true);
  const motionMode = useMotionMode();

  useEffect(() => {
    const container = containerRef.current;
    if (!container || motionMode === "off") return;

    // WebGL support test
    try {
      const testCanvas = document.createElement("canvas");
      const gl = testCanvas.getContext("webgl") || testCanvas.getContext("experimental-webgl");
      if (!gl) {
        setWebglSupported(false);
        return;
      }
    } catch {
      setWebglSupported(false);
      return;
    }

    const initialWidth = container.clientWidth || 640;
    const initialHeight = container.clientHeight || 640;

    // Orthographic Camera for exact 1:1 pixel projection (guarantees zero clipping)
    const camera = new THREE.OrthographicCamera(
      -initialWidth / 2,
      initialWidth / 2,
      initialHeight / 2,
      -initialHeight / 2,
      0.1,
      1000
    );
    camera.position.set(0, 0, 400);
    camera.lookAt(0, 0, 0);

    const scene = new THREE.Scene();

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(initialWidth, initialHeight);
      container.appendChild(renderer.domElement);
    } catch {
      setWebglSupported(false);
      return;
    }

    const canvasDom = renderer.domElement;
    const handleContextLost = (e: Event) => {
      e.preventDefault();
    };
    canvasDom.addEventListener("webglcontextlost", handleContextLost, false);

    // Root rotating globe group
    const globeGroup = new THREE.Group();
    scene.add(globeGroup);

    // 1. Water: Clean filled disc / sphere behind nodes in dark orange-tinted black (#0d0805)
    // Opacity 0.75 dims back nodes to ~25% opacity so the back never disappears
    const waterGeo = new THREE.SphereGeometry(GLOBE_CONFIG.BASE_RADIUS - 0.5, 48, 48);
    const waterMat = new THREE.MeshBasicMaterial({
      color: GLOBE_CONFIG.WATER_COLOR,
      transparent: true,
      opacity: GLOBE_CONFIG.WATER_OPACITY,
    });
    const waterMesh = new THREE.Mesh(waterGeo, waterMat);
    globeGroup.add(waterMesh);

    // 2. Rim Outline: 1px orange circular rim outline at ~20% opacity
    const rimCurve = new THREE.EllipseCurve(0, 0, GLOBE_CONFIG.BASE_RADIUS, GLOBE_CONFIG.BASE_RADIUS, 0, 2 * Math.PI, false, 0);
    const rimPoints = rimCurve.getPoints(128);
    const rimGeo = new THREE.BufferGeometry().setFromPoints(rimPoints);
    const rimMat = new THREE.LineBasicMaterial({
      color: 0xff4d00,
      transparent: true,
      opacity: GLOBE_CONFIG.RIM_OPACITY,
      linewidth: 1,
    });
    const rimLine = new THREE.LineLoop(rimGeo, rimMat);
    rimLine.position.z = 0;
    scene.add(rimLine);

    // 3. Real Land Nodes: 448 nodes strictly on continents (oceans have no nodes)
    const nodes: LandNode[] = EARTH_LAND_NODES;
    const nodeCount = nodes.length;

    // Convert unit sphere coordinates to base radius
    const baseNodePositions: THREE.Vector3[] = nodes.map(
      (n) => new THREE.Vector3(n.x * GLOBE_CONFIG.BASE_RADIUS, n.y * GLOBE_CONFIG.BASE_RADIUS, n.z * GLOBE_CONFIG.BASE_RADIUS)
    );

    // Identify hub nodes (~16 distributed across all continents)
    const hubIndices = new Set<number>();
    const regions = [0, 1, 2, 3, 4, 5];
    regions.forEach((r) => {
      const regionNodes = nodes.map((n, idx) => ({ ...n, idx })).filter((n) => n.region === r);
      // Pick 2-3 hubs per region
      const count = r === 4 || r === 0 || r === 3 ? 3 : 2;
      for (let k = 0; k < count && k < regionNodes.length; k++) {
        const step = Math.floor(regionNodes.length / (count + 1));
        hubIndices.add(regionNodes[(k + 1) * step].idx);
      }
    });

    // Create instanced nodes
    const nodeGeo = new THREE.SphereGeometry(1, 10, 10);
    const nodeMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const instancedNodes = new THREE.InstancedMesh(nodeGeo, nodeMat, nodeCount);

    const dummy = new THREE.Object3D();
    for (let i = 0; i < nodeCount; i++) {
      const pos = baseNodePositions[i];
      const isHub = hubIndices.has(i);

      const size = isHub
        ? GLOBE_CONFIG.HUB_NODE_SIZE
        : THREE.MathUtils.lerp(GLOBE_CONFIG.MIN_NODE_SIZE, GLOBE_CONFIG.MAX_NODE_SIZE, (i % 7) / 7);

      dummy.position.copy(pos);
      dummy.scale.set(size, size, size);
      dummy.updateMatrix();
      instancedNodes.setMatrixAt(i, dummy.matrix);

      const cluster = GLOBE_CONFIG.CLUSTERS[nodes[i].region] || GLOBE_CONFIG.CLUSTERS[0];
      const color = new THREE.Color(cluster.baseColor);
      instancedNodes.setColorAt(i, color);
    }
    instancedNodes.instanceMatrix.needsUpdate = true;
    if (instancedNodes.instanceColor) instancedNodes.instanceColor.needsUpdate = true;
    globeGroup.add(instancedNodes);

    // 4. Intra-continental Edges: Connect each node to 2-3 nearest neighbors in the SAME continent
    const edgePairs: Array<[number, number]> = [];
    const edgeSet = new Set<string>();
    const adjacency: number[][] = Array.from({ length: nodeCount }, () => []);

    for (let i = 0; i < nodeCount; i++) {
      const currentRegion = nodes[i].region;
      // Gather distances to nodes in same continent
      const localNeighbors: Array<{ idx: number; dist: number }> = [];
      for (let j = 0; j < nodeCount; j++) {
        if (i !== j && nodes[j].region === currentRegion) {
          localNeighbors.push({
            idx: j,
            dist: baseNodePositions[i].distanceTo(baseNodePositions[j]),
          });
        }
      }
      localNeighbors.sort((a, b) => a.dist - b.dist);

      for (let k = 0; k < Math.min(GLOBE_CONFIG.NEAREST_NEIGHBORS, localNeighbors.length); k++) {
        const neighborIdx = localNeighbors[k].idx;
        const key = i < neighborIdx ? `${i}-${neighborIdx}` : `${neighborIdx}-${i}`;
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          edgePairs.push([i, neighborIdx]);
          adjacency[i].push(neighborIdx);
          adjacency[neighborIdx].push(i);
        }
      }
    }

    // Static Intra-Continent Edges Buffer
    const lineCoords = new Float32Array(edgePairs.length * 6);
    for (let e = 0; e < edgePairs.length; e++) {
      const [u, v] = edgePairs[e];
      const p1 = baseNodePositions[u];
      const p2 = baseNodePositions[v];
      lineCoords[e * 6 + 0] = p1.x;
      lineCoords[e * 6 + 1] = p1.y;
      lineCoords[e * 6 + 2] = p1.z;
      lineCoords[e * 6 + 3] = p2.x;
      lineCoords[e * 6 + 4] = p2.y;
      lineCoords[e * 6 + 5] = p2.z;
    }

    const intraEdgesGeo = new THREE.BufferGeometry();
    intraEdgesGeo.setAttribute("position", new THREE.BufferAttribute(lineCoords, 3));
    const intraEdgesMat = new THREE.LineBasicMaterial({
      color: 0xff4d00,
      transparent: true,
      opacity: GLOBE_CONFIG.EDGE_OPACITY,
      linewidth: 1,
    });
    const intraEdgesMesh = new THREE.LineSegments(intraEdgesGeo, intraEdgesMat);
    globeGroup.add(intraEdgesMesh);

    // 5. Inter-Continental Curved Arcs Across Oceans (supply chains connecting continents)
    // Quadratic Bezier curves rising slightly above the sphere surface
    const oceanArcPairs: Array<[number, number]> = [
      // North America <-> Europe (transatlantic)
      [Array.from(hubIndices)[0] || 10, Array.from(hubIndices)[4] || 120],
      [15, 125],
      [35, 130],
      // Europe <-> Asia (Eurasia routes)
      [125, 220],
      [135, 230],
      [140, 250],
      // Asia <-> North America (transpacific)
      [220, 25],
      [235, 45],
      [245, 60],
      // North America <-> South America
      [40, 95],
      [50, 105],
      // Europe <-> Africa
      [128, 160],
      [132, 170],
      // Africa <-> Asia / Middle East
      [165, 230],
      [180, 240],
      // Asia <-> Oceania
      [250, 420],
      [260, 430],
      // South America <-> Africa (South Atlantic)
      [100, 175],
      [110, 185],
      // North America <-> Oceania
      [70, 435],
    ];

    const ARC_SEGMENTS = 20;
    const arcPathPoints: THREE.Vector3[][] = [];
    const allArcLinePoints: number[] = [];

    oceanArcPairs.forEach(([u, v]) => {
      const p1 = baseNodePositions[u] || baseNodePositions[0];
      const p2 = baseNodePositions[v] || baseNodePositions[1];

      // Midpoint lifted above sphere
      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
      const chordDist = p1.distanceTo(p2);
      // Lift proportional to distance across ocean
      const lift = GLOBE_CONFIG.BASE_RADIUS + chordDist * 0.18;
      mid.normalize().multiplyScalar(lift);

      // Curve samples
      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      const pts = curve.getPoints(ARC_SEGMENTS);
      arcPathPoints.push(pts);

      for (let s = 0; s < pts.length - 1; s++) {
        allArcLinePoints.push(pts[s].x, pts[s].y, pts[s].z, pts[s + 1].x, pts[s + 1].y, pts[s + 1].z);
      }
    });

    const oceanArcsGeo = new THREE.BufferGeometry();
    oceanArcsGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(allArcLinePoints), 3));
    const oceanArcsMat = new THREE.LineBasicMaterial({
      color: 0xff5a12,
      transparent: true,
      opacity: GLOBE_CONFIG.ARC_OPACITY,
      linewidth: 1,
    });
    const oceanArcsMesh = new THREE.LineSegments(oceanArcsGeo, oceanArcsMat);
    globeGroup.add(oceanArcsMesh);

    // 6. Travelling Pulses (3 to 5 travelling along edges & ocean arcs)
    const pulseCount = GLOBE_CONFIG.ACTIVE_PULSES_COUNT;
    const pulseGeo = new THREE.SphereGeometry(1.2, 8, 8);
    const pulseMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const instancedPulses = new THREE.InstancedMesh(pulseGeo, pulseMat, pulseCount);

    const pulseStates = Array.from({ length: pulseCount }, (_, i) => ({
      isArc: i % 2 === 0, // half on continent edges, half on ocean arcs
      index: i % 2 === 0 ? i % arcPathPoints.length : i % edgePairs.length,
      progress: Math.random(),
      speed: GLOBE_CONFIG.PULSE_SPEED * (motionMode === "reduced" ? 0.3 : 1.0),
    }));
    globeGroup.add(instancedPulses);

    // 7. Spontaneous & Hover Highlight Line
    const highlightGeo = new THREE.BufferGeometry();
    const highlightMat = new THREE.LineBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.0,
      linewidth: 1.5,
    });
    const highlightMesh = new THREE.LineSegments(highlightGeo, highlightMat);
    globeGroup.add(highlightMesh);

    let highlightProgress = 0;
    let highlightTimer = 0;

    const triggerHighlight = (nodeIdx: number) => {
      highlightProgress = 1.0;
      const nbrs = adjacency[nodeIdx];
      if (nbrs && nbrs.length > 0) {
        const hCoords = new Float32Array(nbrs.length * 6);
        const origin = baseNodePositions[nodeIdx];

        nbrs.forEach((nbr, idx) => {
          const dest = baseNodePositions[nbr];
          hCoords[idx * 6 + 0] = origin.x;
          hCoords[idx * 6 + 1] = origin.y;
          hCoords[idx * 6 + 2] = origin.z;
          hCoords[idx * 6 + 3] = dest.x;
          hCoords[idx * 6 + 4] = dest.y;
          hCoords[idx * 6 + 5] = dest.z;
        });

        highlightGeo.setAttribute("position", new THREE.BufferAttribute(hCoords, 3));
      }
    };

    // 8. Mouse interaction (exact screen-space raycasting)
    let mousePos = { x: -9999, y: -9999 };
    let mouseClientPos = { x: 0, y: 0 };

    const onMouseMove = (evt: MouseEvent) => {
      const rect = canvasDom.getBoundingClientRect();
      // Relative to center of canvas
      mousePos = {
        x: evt.clientX - rect.left - rect.width / 2,
        y: -(evt.clientY - rect.top - rect.height / 2),
      };
      mouseClientPos = { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
    };

    const onMouseLeave = () => {
      mousePos = { x: -9999, y: -9999 };
      setHoveredNode(null);
    };

    canvasDom.addEventListener("mousemove", onMouseMove);
    canvasDom.addEventListener("mouseleave", onMouseLeave);

    // 9. ResizeObserver: Dynamic Radius & Orthographic Scaling (Zero Clipping)
    let currentScale = 1.0;
    const applySize = (w: number, h: number) => {
      if (!renderer || w <= 0 || h <= 0) return;

      // Ensure explicit canvas dimension
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      camera.left = -w / 2;
      camera.right = w / 2;
      camera.top = h / 2;
      camera.bottom = -h / 2;
      camera.updateProjectionMatrix();

      // Dynamic radius: fits within min(w, h) / 2 - padding
      const maxRadius = Math.min(w, h) / 2 - GLOBE_CONFIG.CONTAINER_PADDING;
      currentScale = Math.max(0.2, maxRadius / GLOBE_CONFIG.BASE_RADIUS);

      globeGroup.scale.set(currentScale, currentScale, currentScale);
      rimLine.scale.set(currentScale, currentScale, currentScale);
    };

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          applySize(width, height);
        }
      }
    });
    resizeObserver.observe(container);
    applySize(initialWidth, initialHeight);

    // 10. Animation Loop
    let isVisible = true;
    const intersectionObserver = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
    });
    intersectionObserver.observe(container);

    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      if (!isVisible || document.hidden) return;

      // Slow continuous rotation
      globeGroup.rotation.y += GLOBE_CONFIG.ROTATION_SPEED_Y;
      globeGroup.rotation.x += GLOBE_CONFIG.ROTATION_SPEED_X;

      // Update travelling pulses
      const pulseDummy = new THREE.Object3D();
      for (let p = 0; p < pulseCount; p++) {
        const state = pulseStates[p];
        state.progress += state.speed;
        if (state.progress >= 1.0) {
          state.progress = 0;
          if (state.isArc) {
            state.index = Math.floor(Math.random() * arcPathPoints.length);
          } else {
            state.index = Math.floor(Math.random() * edgePairs.length);
          }
        }

        let pulsePos: THREE.Vector3 | null = null;
        if (state.isArc) {
          const pts = arcPathPoints[state.index];
          if (pts && pts.length > 0) {
            const sampleIdx = Math.min(pts.length - 1, Math.floor(state.progress * (pts.length - 1)));
            pulsePos = pts[sampleIdx];
          }
        } else {
          const [u, v] = edgePairs[state.index] || [0, 1];
          const p1 = baseNodePositions[u];
          const p2 = baseNodePositions[v];
          if (p1 && p2) {
            pulsePos = new THREE.Vector3().lerpVectors(p1, p2, state.progress);
          }
        }

        if (pulsePos) {
          pulseDummy.position.copy(pulsePos);
          pulseDummy.scale.set(1.0, 1.0, 1.0);
          pulseDummy.updateMatrix();
          instancedPulses.setMatrixAt(p, pulseDummy.matrix);
        }
      }
      instancedPulses.instanceMatrix.needsUpdate = true;

      // Spontaneous highlight
      highlightTimer++;
      if (highlightTimer > GLOBE_CONFIG.HIGHLIGHT_INTERVAL_TICKS) {
        highlightTimer = 0;
        const randNode = Math.floor(Math.random() * nodeCount);
        triggerHighlight(randNode);
      }

      if (highlightProgress > 0) {
        highlightProgress -= 0.015;
        highlightMat.opacity = Math.max(0, highlightProgress * 0.7);
      }

      // Hover detection on front nodes
      if (mousePos.x !== -9999) {
        let closestIdx = -1;
        let closestDist = 14; // pixels tolerance

        const tempVec = new THREE.Vector3();
        for (let i = 0; i < nodeCount; i++) {
          tempVec.copy(baseNodePositions[i]);
          tempVec.applyEuler(globeGroup.rotation);
          // Only check front hemisphere nodes
          if (tempVec.z > 0) {
            const screenX = tempVec.x * currentScale;
            const screenY = tempVec.y * currentScale;
            const dist = Math.hypot(screenX - mousePos.x, screenY - mousePos.y);
            if (dist < closestDist) {
              closestDist = dist;
              closestIdx = i;
            }
          }
        }

        if (closestIdx !== -1) {
          triggerHighlight(closestIdx);
          const n = nodes[closestIdx];
          const cluster = GLOBE_CONFIG.CLUSTERS[n.region] || GLOBE_CONFIG.CLUSTERS[0];
          setHoveredNode({
            title: `Entity Node #${1000 + closestIdx} [${n.lat.toFixed(1)}°, ${n.lon.toFixed(1)}°]`,
            type: cluster.type,
            region: cluster.region,
            x: mouseClientPos.x,
            y: mouseClientPos.y,
          });
        } else {
          setHoveredNode(null);
        }
      }

      if (renderer) {
        renderer.render(scene, camera);
      }
    };
    animate();

    return () => {
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      cancelAnimationFrame(animId);
      canvasDom.removeEventListener("mousemove", onMouseMove);
      canvasDom.removeEventListener("mouseleave", onMouseLeave);
      canvasDom.removeEventListener("webglcontextlost", handleContextLost);

      waterGeo.dispose();
      waterMat.dispose();
      rimGeo.dispose();
      rimMat.dispose();
      nodeGeo.dispose();
      nodeMat.dispose();
      intraEdgesGeo.dispose();
      intraEdgesMat.dispose();
      oceanArcsGeo.dispose();
      oceanArcsMat.dispose();
      pulseGeo.dispose();
      pulseMat.dispose();
      highlightGeo.dispose();
      highlightMat.dispose();

      if (renderer) {
        renderer.dispose();
        if (renderer.domElement && renderer.domElement.parentNode) {
          renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
      }
    };
  }, [motionMode]);

  if (!webglSupported) {
    return (
      <div className="relative w-full h-full flex items-center justify-center">
        <div className="w-64 h-64 rounded-full border border-[#FF4D00]/40 flex items-center justify-center">
          <span className="text-xs font-mono text-[#FF7A1A]">DOCUMENT NETWORK TOPOLOGY</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center pointer-events-auto">
      <div ref={containerRef} className={className} />

      {/* Tooltip on hover near a node */}
      {hoveredNode && (
        <div
          className="absolute z-30 pointer-events-none px-3.5 py-2 rounded-xl bg-[#0B0B0C]/95 border border-[#FF4D00]/50 text-white text-[11px] shadow-2xl backdrop-blur-md transform -translate-x-1/2 -translate-y-full -mt-3 transition-opacity"
          style={{ left: `${hoveredNode.x}px`, top: `${hoveredNode.y}px` }}
        >
          <span className="font-semibold text-[#FF7A1A] block">{hoveredNode.type}</span>
          <span className="text-white/60 block text-[10px] mt-0.5">{hoveredNode.region} • {hoveredNode.title}</span>
        </div>
      )}
    </div>
  );
}
