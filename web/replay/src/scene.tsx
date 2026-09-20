import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { enuToView, type Sample } from "./contracts.js";

export default function Scene({
  sample,
  samples,
  rotorFlight,
  visible,
  onFailure,
}: {
  sample: Sample;
  samples: Sample[];
  rotorFlight: boolean;
  visible: boolean;
  onFailure: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const draw = useRef<((s: Sample) => void) | null>(null);
  const current = useRef(sample);
  const cameraView = useRef<((name: string) => void) | null>(null);
  current.current = sample;
  useEffect(() => {
    const element = host.current!;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "low-power",
      });
    } catch {
      onFailure();
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 100);
    camera.position.set(1.5, 2.1, 1.9);
    camera.lookAt(0, 1.3, -0.4);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.3, -0.4);
    controls.minDistance = 1;
    controls.maxDistance = 15;
    controls.enableDamping = false;
    controls.update();
    const aircraft = new THREE.Group();
    // Original schematic body: +X nose, +Y left, +Z up in FLU.
    const material = new THREE.MeshBasicMaterial({ color: 0x67e8f9 });
    aircraft.add(
      new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.08, 0.045), material),
    );
    for (const angle of rotorFlight
      ? [Math.PI / 4, -Math.PI / 4]
      : [0, Math.PI / 2]) {
      const arm = new THREE.Mesh(
        new THREE.BoxGeometry(rotorFlight ? 0.46 : 0.55, 0.025, 0.025),
        material,
      );
      arm.rotation.z = angle;
      aircraft.add(arm);
    }
    const a = 0.23 / Math.SQRT2;
    const positions = rotorFlight
      ? [
          [a, a],
          [-a, a],
          [-a, -a],
          [a, -a],
        ]
      : [
          [0.25, 0],
          [-0.25, 0],
          [0, 0.25],
          [0, -0.25],
        ];
    const thrustArrows: THREE.ArrowHelper[] = [];
    for (const [x, y] of positions) {
      const rotor = new THREE.Mesh(
        new THREE.TorusGeometry(0.075, 0.012, 6, 20),
        material,
      );
      rotor.position.set(x, y, 0.025);
      aircraft.add(rotor);
      if (rotorFlight) {
        const arrow = new THREE.ArrowHelper(
          new THREE.Vector3(0, 0, 1),
          new THREE.Vector3(x, y, 0.03),
          0.2,
          0x4ade80,
          0.03,
          0.02,
        );
        thrustArrows.push(arrow);
        aircraft.add(arrow);
      }
    }
    const nose = new THREE.Mesh(
      new THREE.ConeGeometry(0.055, 0.15, 12),
      new THREE.MeshBasicMaterial({ color: 0xfbbf24 }),
    );
    nose.rotation.z = -Math.PI / 2;
    nose.position.x = 0.17;
    aircraft.add(nose);
    scene.add(aircraft);
    const path = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(
        samples.map((s) => new THREE.Vector3(...enuToView(s.position_m))),
      ),
      new THREE.LineBasicMaterial({ color: 0x7b9bb0 }),
    );
    scene.add(path);
    const target = new THREE.Mesh(
      new THREE.SphereGeometry(0.07, 12, 8),
      new THREE.MeshBasicMaterial({ color: 0xfbbf24, wireframe: true }),
    );
    scene.add(target, new THREE.GridHelper(6, 12, 0x52748c, 0x29465c));
    const basis = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(1, 0, 0),
      -Math.PI / 2,
    );
    const body = new THREE.Quaternion();
    let disposed = false;
    draw.current = (s) => {
      if (disposed) return;
      aircraft.position.set(...enuToView(s.position_m));
      const [w, x, y, z] = s.quaternion_wxyz;
      aircraft.quaternion.copy(basis).multiply(body.set(x, y, z, w));
      target.position.set(...enuToView(s.target_m));
      thrustArrows.forEach((arrow, i) =>
        arrow.setLength(
          0.02 + (0.3 * (s.rotor_thrust_n?.[i] ?? 0)) / 5,
          0.025,
          0.015,
        ),
      );
      renderer.render(scene, camera);
    };
    const changed = () => draw.current?.(current.current);
    controls.addEventListener("change", changed);
    cameraView.current = (name) => {
      camera.position.set(
        ...((name === "top"
          ? [0, 4, 0.01]
          : name === "side"
            ? [2.6, 1.5, 0]
            : [1.5, 2.1, 1.9]) as [number, number, number]),
      );
      controls.target.set(0, 1.3, -0.4);
      controls.update();
      changed();
    };
    const resize = new ResizeObserver(() => {
      const width = element.clientWidth,
        height = element.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      draw.current?.(current.current);
    });
    const lost = (event: Event) => {
      event.preventDefault();
      onFailure();
    };
    renderer.domElement.addEventListener("webglcontextlost", lost);
    renderer.domElement.setAttribute("aria-hidden", "true");
    element.append(renderer.domElement);
    resize.observe(element);
    return () => {
      disposed = true;
      draw.current = null;
      cameraView.current = null;
      controls.removeEventListener("change", changed);
      controls.dispose();
      resize.disconnect();
      renderer.domElement.removeEventListener("webglcontextlost", lost);
      const geometries = new Set<THREE.BufferGeometry>(),
        materials = new Set<THREE.Material>();
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        if (mesh.geometry) geometries.add(mesh.geometry);
        if (mesh.material)
          (Array.isArray(mesh.material)
            ? mesh.material
            : [mesh.material]
          ).forEach((m) => materials.add(m));
      });
      geometries.forEach((g) => g.dispose());
      materials.forEach((m) => m.dispose());
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [onFailure, samples, rotorFlight]);
  useEffect(() => {
    if (visible) draw.current?.(sample);
  }, [sample, visible]);
  return (
    <>
      <div className="al-webgl" ref={host} />
      <div className="al-camera" aria-label="3D camera views">
        <button type="button" onClick={() => cameraView.current?.("orbit")}>
          Orbit view
        </button>
        <button type="button" onClick={() => cameraView.current?.("top")}>
          Top view
        </button>
        <button type="button" onClick={() => cameraView.current?.("side")}>
          Side view
        </button>
      </div>
    </>
  );
}
