"use client";

import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { Center, ContactShadows, Html, OrbitControls } from "@react-three/drei";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsType } from "three-stdlib";

export type Measurements = {
  height_cm?: number;
  chest_cm?: number;
  waist_cm?: number;
  hip_cm?: number;
  shoulder_width_cm?: number;
  inseam_cm?: number;
};

function Surface({ object, wireframe, targetHeight }: { object: THREE.Object3D; wireframe: boolean; targetHeight: number }) {
  const model = useMemo(() => {
    const copy = object.clone(true);
    copy.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.material = new THREE.MeshStandardMaterial({
          color: "#96ab94",
          roughness: 0.68,
          metalness: 0.08,
          wireframe,
          side: THREE.DoubleSide,
        });
        child.castShadow = true;
      }
    });
    const box = new THREE.Box3().setFromObject(copy);
    const sizeY = box.getSize(new THREE.Vector3()).y;
    if (sizeY > 0) {
      copy.scale.setScalar(targetHeight / sizeY);
    }
    return copy;
  }, [object, targetHeight]);

  useEffect(() => {
    model.traverse((child) => {
      if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
        child.material.wireframe = wireframe;
        child.material.needsUpdate = true;
      }
    });
  }, [model, wireframe]);

  useEffect(() => () => model.traverse((child) => {
    if (child instanceof THREE.Mesh) (child.material as THREE.Material).dispose();
  }), [model]);

  return <Center top position={[0, 0.025, 0]}><primitive object={model} /></Center>;
}

function Sample({ wireframe }: { wireframe: boolean }) {
  const object = useLoader(OBJLoader, "/sample-body.obj");
  return <Surface object={object} wireframe={wireframe} targetHeight={1.75} />;
}

function Result({ url, wireframe, targetHeightCm }: { url: string; wireframe: boolean; targetHeightCm?: number }) {
  const model = useLoader(GLTFLoader, url);
  return <Surface object={model.scene} wireframe={wireframe} targetHeight={targetHeightCm ? targetHeightCm / 100 : 1.75} />;
}

function MeasurementRings({ targetHeight, measurements }: { targetHeight: number; measurements: Measurements }) {
  const chestR = measurements.chest_cm ? ((measurements.chest_cm / 100) / (2 * Math.PI)) * 1.02 : 0.17;
  const waistR = measurements.waist_cm ? ((measurements.waist_cm / 100) / (2 * Math.PI)) * 1.03 : 0.14;
  const hipR = measurements.hip_cm ? ((measurements.hip_cm / 100) / (2 * Math.PI)) * 1.02 : 0.18;

  return (
    <group position={[0, 0.025, 0]}>
      {/* Chest Ring */}
      {measurements.chest_cm && (
        <group position={[0, targetHeight * 0.715, 0]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[chestR, 0.003, 16, 64]} />
            <meshBasicMaterial color="#17694c" />
          </mesh>
          <Html position={[chestR + 0.04, 0, 0]} center style={{ pointerEvents: "none" }}>
            <div className="ring-3d-tag">Ngực {measurements.chest_cm}cm</div>
          </Html>
        </group>
      )}

      {/* Waist Ring */}
      {measurements.waist_cm && (
        <group position={[0, targetHeight * 0.595, 0]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[waistR, 0.003, 16, 64]} />
            <meshBasicMaterial color="#2ed573" />
          </mesh>
          <Html position={[waistR + 0.04, 0, 0]} center style={{ pointerEvents: "none" }}>
            <div className="ring-3d-tag active">Eo {measurements.waist_cm}cm</div>
          </Html>
        </group>
      )}

      {/* Hip Ring */}
      {measurements.hip_cm && (
        <group position={[0, targetHeight * 0.505, 0]}>
          <mesh rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[hipR, 0.003, 16, 64]} />
            <meshBasicMaterial color="#17694c" />
          </mesh>
          <Html position={[hipR + 0.04, 0, 0]} center style={{ pointerEvents: "none" }}>
            <div className="ring-3d-tag">Mông {measurements.hip_cm}cm</div>
          </Html>
        </group>
      )}
    </group>
  );
}

function Controls({ reset, autoRotate }: { reset: number; autoRotate: boolean }) {
  const controls = useRef<OrbitControlsType>(null);
  const camera = useThree(state => state.camera);
  useEffect(() => {
    camera.position.set(0, 0.95, 3.1);
    if (controls.current) {
      controls.current.target.set(0, 0.88, 0);
      controls.current.update();
    }
  }, [reset, camera]);
  return <OrbitControls ref={controls} target={[0, 0.88, 0]} enablePan={false} minDistance={1.8} maxDistance={5} maxPolarAngle={Math.PI / 1.85} minPolarAngle={0.2} autoRotate={autoRotate} autoRotateSpeed={0.65} />;
}

export default function BodyViewer({
  url,
  wireframe,
  reset,
  autoRotate,
  targetHeightCm,
  showRings,
  measurements,
}: {
  url?: string;
  wireframe: boolean;
  reset: number;
  autoRotate: boolean;
  targetHeightCm?: number;
  showRings?: boolean;
  measurements?: Measurements;
}) {
  const actualHeight = targetHeightCm ? targetHeightCm / 100 : 1.75;

  return (
    <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0.95, 3.1], fov: 42 }} gl={{ antialias: true, alpha: true }} fallback={<p className="viewer-fallback">Trình duyệt chưa hỗ trợ WebGL. Hãy bật tăng tốc đồ họa hoặc mở bằng Chrome.</p>}>
      <ambientLight intensity={1.2} />
      <directionalLight position={[3, 5, 4]} intensity={2.6} />
      <directionalLight position={[-3, 2, -2]} intensity={1.8} color="#eaf6df" />
      <Suspense fallback={null}>
        {url ? <Result url={url} wireframe={wireframe} targetHeightCm={targetHeightCm} /> : <Sample wireframe={wireframe} />}
      </Suspense>
      {showRings && measurements && (
        <MeasurementRings targetHeight={actualHeight} measurements={measurements} />
      )}
      <ContactShadows position={[0, 0.01, 0]} opacity={0.5} scale={2} blur={1.2} far={1} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}><ringGeometry args={[0.60, 0.605, 96]} /><meshBasicMaterial color="#bcc9bd" side={THREE.DoubleSide} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.61, 96]} /><meshBasicMaterial color="#ccd7cb" transparent opacity={0.45} /></mesh>
      <Controls reset={reset} autoRotate={autoRotate} />
    </Canvas>
  );
}
