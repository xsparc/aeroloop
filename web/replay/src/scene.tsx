import { useEffect, useRef } from "react";
import * as THREE from "three";
import { enuToView, type Sample } from "./contracts.js";

export default function Scene({ sample, visible, onFailure }: { sample: Sample; visible: boolean; onFailure: () => void }) {
  const host = useRef<HTMLDivElement>(null);
  const draw = useRef<((s: Sample) => void) | null>(null);
  const current = useRef(sample);
  current.current = sample;
  useEffect(() => {
    const element = host.current!;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" }); }
    catch { onFailure(); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, .05, 100);
    camera.position.set(3.3, 2.8, 3.8); camera.lookAt(0, 1, -.3);
    const aircraft = new THREE.Group();
    // Original schematic body: +X nose, +Y left, +Z up in FLU.
    const material = new THREE.MeshBasicMaterial({ color: 0x67e8f9 });
    aircraft.add(new THREE.Mesh(new THREE.BoxGeometry(.55, .055, .055), material));
    aircraft.add(new THREE.Mesh(new THREE.BoxGeometry(.055, .55, .055), material));
    for (const [x, y] of [[.25, 0], [-.25, 0], [0, .25], [0, -.25]]) {
      const rotor = new THREE.Mesh(new THREE.TorusGeometry(.075, .012, 6, 20), material);
      rotor.position.set(x, y, .025); aircraft.add(rotor);
    }
    const nose = new THREE.Mesh(new THREE.ConeGeometry(.055, .15, 12), new THREE.MeshBasicMaterial({ color: 0xfbbf24 }));
    nose.rotation.z = -Math.PI / 2; nose.position.x = .17; aircraft.add(nose);
    scene.add(aircraft);
    const target = new THREE.Mesh(new THREE.SphereGeometry(.07, 12, 8), new THREE.MeshBasicMaterial({ color: 0xfbbf24, wireframe: true }));
    scene.add(target, new THREE.GridHelper(6, 12, 0x52748c, 0x29465c));
    const basis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);
    const body = new THREE.Quaternion();
    let disposed = false;
    draw.current = s => {
      if (disposed) return;
      aircraft.position.set(...enuToView(s.position_m));
      const [w, x, y, z] = s.quaternion_wxyz;
      aircraft.quaternion.copy(basis).multiply(body.set(x, y, z, w));
      target.position.set(...enuToView(s.target_m));
      renderer.render(scene, camera);
    };
    const resize = new ResizeObserver(() => {
      const width = element.clientWidth, height = element.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix();
      draw.current?.(current.current);
    });
    const lost = (event: Event) => { event.preventDefault(); onFailure(); };
    renderer.domElement.addEventListener("webglcontextlost", lost);
    renderer.domElement.setAttribute("aria-hidden", "true");
    element.append(renderer.domElement); resize.observe(element);
    return () => {
      disposed = true; draw.current = null; resize.disconnect();
      renderer.domElement.removeEventListener("webglcontextlost", lost);
      const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
      scene.traverse(object => {
        const mesh = object as THREE.Mesh;
        if (mesh.geometry) geometries.add(mesh.geometry);
        if (mesh.material) (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach(m => materials.add(m));
      });
      geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose());
      renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    };
  }, [onFailure]);
  useEffect(() => { if (visible) draw.current?.(sample); }, [sample, visible]);
  return <div className="al-webgl" ref={host} />;
}
