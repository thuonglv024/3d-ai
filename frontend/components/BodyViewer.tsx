"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { Center, ContactShadows, Line, OrbitControls } from "@react-three/drei";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";
import { VIEWER_CONFIG, defaultFrame, frameForBounds, type ViewerFrame } from "../lib/viewerConfig";
import type {MeasurementDetail} from "../lib/useBodyScan";
import type { FitBand } from "../lib/fitMap";
import type { OrbitControls as OrbitControlsType } from "three-stdlib";

export type Section = {key:string;label:string;target_cm:number;model_cm:number;fit_error_cm:number;points_m:[number,number,number][]};
const SECTION_COLORS: Record<string,string> = {chest_cm:"#194e3d",waist_cm:"#a0521e",hip_cm:"#285b7e",chest:"#194e3d",waist:"#a0521e",hip:"#285b7e"};
const VIEWS = [{label:"Chính diện",angle:0},{label:"Nghiêng",angle:Math.PI/2},{label:"Sau",angle:Math.PI}];

export type FitColorStop = { ease_cm: number; label: string; color: string };
export type FitRegionBand = {
  from: number;
  to: number;
  color: string;
  label?: string;
  ease_cm?: number | null;
};
export type ContinuousFitHeatmap = {
  mode: "continuous_vertex";
  ease_cm: number;
  taper_cm: number;
  arm_x_fraction: number;
  garment_length_cm: number | null;
  garment_length_measurement_point?: string;
  shoulder_level: number;
  hip_level: number;
  color_stops: FitColorStop[];
  unknown_color: string;
  unverified: boolean;
  sleeve_ease_cm?: number | null;
  sleeve_length_cm?: number | null;
};
/** UI-only bucket map: colour whole body bands (chest/waist) instead of a field. */
export type RegionFitHeatmap = {
  mode: "region_buckets";
  regions: FitRegionBand[];
  unknown_color: string;
  arm_x_fraction: number;
  garment_length_cm?: number | null;
  shoulder_level?: number;
  hip_level?: number;
  unverified: boolean;
};
export type FitHeatmap = ContinuousFitHeatmap | RegionFitHeatmap;

function applyEaseColor(ease: number, stops: { ease: number; color: THREE.Color }[], target: THREE.Color) {
  if (!stops.length) return target;
  if (ease <= stops[0].ease) return target.copy(stops[0].color);
  for (let i = 1; i < stops.length; i += 1) {
    const left = stops[i - 1];
    const right = stops[i];
    if (ease <= right.ease) {
      const t = (ease - left.ease) / Math.max(right.ease - left.ease, 1e-6);
      return target.copy(left.color).lerp(right.color, t);
    }
  }
  return target.copy(stops[stops.length - 1].color);
}

function Surface({ object, wireframe, targetHeight, preserveOrigin = false, studio=false, technical=false, points=false, fitBands, fitHeatmap, bodyHeightCm, onFrame }: { object: THREE.Object3D; wireframe: boolean; targetHeight: number; preserveOrigin?: boolean; studio?:boolean;technical?:boolean;points?:boolean;fitBands?:FitBand[];fitHeatmap?:FitHeatmap;bodyHeightCm?:number;onFrame?:(frame:ViewerFrame)=>void }) {
  const { model, frame } = useMemo(() => {
    const copy = object.clone(true);
    const bounds=new THREE.Box3().setFromObject(copy), height=bounds.max.y-bounds.min.y;
    const scale = height > 0 ? targetHeight / height : 1;
    copy.scale.setScalar(scale);
    copy.updateMatrixWorld(true);
    // Measure the *scaled* mesh: GLB roots may carry their own transform, so
    // multiplying the raw bbox by the scale can miss the real head top.
    const scaledBounds = new THREE.Box3().setFromObject(copy);
    const frame = frameForBounds(
      scaledBounds.min.y + VIEWER_CONFIG.offsetY,
      scaledBounds.max.y + VIEWER_CONFIG.offsetY,
    );
    const clipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -frame.cutY);
    copy.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        // Own the geometry; never mutate the shared loader cache.
        let geometry=child.geometry.clone();
        if(!preserveOrigin){
          geometry.deleteAttribute("normal");geometry.deleteAttribute("uv");
          const welded=mergeVertices(geometry);geometry.dispose();geometry=welded;
          geometry.computeVertexNormals();
        }
        child.geometry=geometry;
        const regionHeatmap = fitHeatmap?.mode === "region_buckets";
        const continuousHeatmap =
          fitHeatmap?.mode === "continuous_vertex" && fitHeatmap.garment_length_cm != null;
        if (regionHeatmap || continuousHeatmap || fitBands?.length) {
          // Per-vertex fit colours. The bucket map paints whole chest/waist
          // bands (UI only); the continuous field is kept for older payloads,
          // and products without garment data keep the Y-band path.
          const position = geometry.getAttribute("position");
          const colors = new Float32Array(position.count * 3);
          const color = new THREE.Color();
          const realHeightCm = bodyHeightCm ?? 175;
          if (fitHeatmap?.mode === "region_buckets") {
            const armFraction = fitHeatmap.arm_x_fraction ?? 0.18;
            const centerX = (bounds.min.x + bounds.max.x) / 2;
            const gray = new THREE.Color(fitHeatmap.unknown_color || "#c9d1c8");
            const bands = fitHeatmap.regions.map((band) => ({
              ...band,
              three: new THREE.Color(band.color),
            }));
            const shoulder = fitHeatmap.shoulder_level ?? 0.805;
            const hemNorm =
              fitHeatmap.garment_length_cm != null
                ? shoulder - fitHeatmap.garment_length_cm / Math.max(realHeightCm, 1e-6)
                : null;
            for (let i = 0; i < position.count; i++) {
              const normalizedY = (position.getY(i) - bounds.min.y) / Math.max(height, 1e-6);
              const isArm = Math.abs(position.getX(i) - centerX) > armFraction * height;
              const belowHem = hemNorm != null && normalizedY < hemNorm;
              const band = isArm || belowHem
                ? undefined
                : bands.find((item) => normalizedY >= item.from && normalizedY < item.to);
              color.copy(band ? band.three : gray);
              colors[i * 3] = color.r;
              colors[i * 3 + 1] = color.g;
              colors[i * 3 + 2] = color.b;
            }
          } else if (fitHeatmap?.mode === "continuous_vertex" && fitHeatmap.garment_length_cm != null) {
            const shoulder = fitHeatmap.shoulder_level ?? 0.805;
            const hip = fitHeatmap.hip_level ?? 0.534;
            const span = Math.max(shoulder - hip, 1e-6);
            const hemLevel = (shoulder - fitHeatmap.garment_length_cm / Math.max(realHeightCm, 1e-6) - hip) / span;
            const taperLevel = Math.max((fitHeatmap.taper_cm ?? 4) / Math.max(realHeightCm, 1e-6) / span, 1e-6);
            const armFraction = fitHeatmap.arm_x_fraction ?? 0.18;
            const stops = fitHeatmap.color_stops
              .map((stop) => ({ ease: stop.ease_cm, color: new THREE.Color(stop.color) }))
              .sort((a, b) => a.ease - b.ease);
            const gray = new THREE.Color(fitHeatmap.unknown_color || "#c9d1c8");
            const centerX = (bounds.min.x + bounds.max.x) / 2;
            for (let i = 0; i < position.count; i++) {
              const normalizedY = (position.getY(i) - bounds.min.y) / Math.max(height, 1e-6);
              const level = (normalizedY - hip) / span;
              const isArm = Math.abs(position.getX(i) - centerX) > armFraction * height;
              const inTorso = !isArm && level >= hemLevel && level <= 1;
              if (!inTorso) {
                color.copy(gray);
              } else {
                const edge = Math.min(1, Math.max(0, Math.min(
                  (1 - level) / taperLevel,
                  (level - hemLevel) / taperLevel,
                )));
                const ease = fitHeatmap.ease_cm * (0.5 - 0.5 * Math.cos(Math.PI * edge));
                applyEaseColor(ease, stops, color);
              }
              colors[i * 3] = color.r;
              colors[i * 3 + 1] = color.g;
              colors[i * 3 + 2] = color.b;
            }
          } else if (fitBands?.length) {
            for (let i = 0; i < position.count; i++) {
              const normalizedY = (position.getY(i) - bounds.min.y) / Math.max(height, 1e-6);
              const band = fitBands.find((b) => normalizedY >= b.from && normalizedY < b.to);
              color.set(band?.color ?? "#c9d1c8");
              colors[i * 3] = color.r;
              colors[i * 3 + 1] = color.g;
              colors[i * 3 + 2] = color.b;
            }
          }
          geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
        }
        if(studio){
          const p=geometry.getAttribute("position"), coordinates=new Float32Array(p.count*2);
          for(let i=0;i<p.count;i++){
            const y=(p.getY(i)-bounds.min.y)/height, x=Math.abs(p.getX(i))/height;
            coordinates[i*2]=x;coordinates[i*2+1]=y;
          }
          geometry.setAttribute("morphCoord",new THREE.BufferAttribute(coordinates,2));
        }
        const vertexColored = Boolean(
          fitHeatmap?.mode === "region_buckets" ||
          (fitHeatmap?.mode === "continuous_vertex" && fitHeatmap.garment_length_cm != null) ||
          fitBands?.length
        );
        const material = new THREE.MeshStandardMaterial({
          color: vertexColored ? "#ffffff" : technical?"#3d5c4e":studio?"#ffffff":"#4a6858",
          vertexColors: vertexColored,
          roughness: 0.80,
          metalness: 0.04,
          wireframe,
          side: THREE.DoubleSide,
          clippingPlanes: [clipPlane],
          clipShadows: true,
        });
        child.material = material;
        if(studio){
          material.onBeforeCompile=shader=>{
            shader.uniforms.morphSkin={value:new THREE.Color("#cec8bb")};
            shader.uniforms.morphFabric={value:new THREE.Color("#78766b")};
            shader.vertexShader="attribute vec2 morphCoord; varying vec2 vMorphCoord;\n"+shader.vertexShader;
            shader.vertexShader=shader.vertexShader.replace("#include <begin_vertex>","#include <begin_vertex>\nvMorphCoord=morphCoord;");
            shader.fragmentShader="uniform vec3 morphSkin; uniform vec3 morphFabric; varying vec2 vMorphCoord;\n"+shader.fragmentShader;
            // Interpolate coordinates, then shade per fragment: no jagged vertex-color hems.
            shader.fragmentShader=shader.fragmentShader.replace("#include <color_fragment>",`#include <color_fragment>
              float cloth=smoothstep(0.406,0.409,vMorphCoord.y)*(1.0-smoothstep(0.785,0.788,vMorphCoord.y))*(1.0-smoothstep(0.201,0.204,vMorphCoord.x));
              diffuseColor.rgb*=mix(morphSkin,morphFabric,cloth);`);
          };
          material.customProgramCacheKey=()=>"morph-studio-bodysuit-v1";
        }
        child.castShadow = true;
      }
    });
    if(points){
      const cloud=new THREE.Group();copy.updateMatrixWorld(true);
      copy.traverse(child=>{if(child instanceof THREE.Mesh){const geometry=child.geometry.clone();geometry.applyMatrix4(child.matrixWorld);cloud.add(new THREE.Points(geometry,new THREE.PointsMaterial({color:"#194e3d",size:.006,sizeAttenuation:true,clippingPlanes:[clipPlane]})));}});
      return {model: cloud, frame};
    }
    return {model: copy, frame};
  }, [object, targetHeight, preserveOrigin, studio,technical,points,fitBands,fitHeatmap,bodyHeightCm]);

  useEffect(() => {
    onFrame?.(frame);
  }, [frame, onFrame]);

  useEffect(() => {
    model.traverse((child) => {
      if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
        child.material.wireframe = wireframe;
        child.material.needsUpdate = true;
      }
    });
  }, [model, wireframe]);

  useEffect(() => () => model.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.Points) { (child.material as THREE.Material).dispose();child.geometry.dispose(); }
  }), [model]);

  return preserveOrigin ? <group position={[0, 0.025, 0]}><primitive object={model}/></group> : <Center top position={[0, 0.025, 0]}><primitive object={model} /></Center>;
}

function Sample({ wireframe,studio,technical,points }: { wireframe: boolean;studio:boolean;technical:boolean;points:boolean }) {
  const object = useLoader(OBJLoader, "/sample-body.obj");
  return <Surface object={object} wireframe={wireframe} targetHeight={1.75} studio={studio} technical={technical} points={points}/>;
}

function Result({ url, wireframe,studio,technical,points,fitBands,fitHeatmap,bodyHeightCm,onFrame }: { url: string; wireframe: boolean;studio:boolean;technical:boolean;points:boolean;fitBands?:FitBand[];fitHeatmap?:FitHeatmap;bodyHeightCm?:number;onFrame?:(frame:ViewerFrame)=>void }) {
  const model = useLoader(GLTFLoader, url);
  return <Surface object={model.scene} wireframe={wireframe} targetHeight={1.75} preserveOrigin studio={studio} technical={technical} points={points} fitBands={fitBands} fitHeatmap={fitHeatmap} bodyHeightCm={bodyHeightCm} onFrame={onFrame}/>;
}

function MeasurementRings({ heightCm, sections }: { heightCm:number; sections:Section[] }) {
  const scale=1.75/(heightCm/100);
  return <group position={[0,.025,0]}>{sections.map(section=>{
    const points=section.points_m.map(p=>[p[0]*scale,p[1]*scale,p[2]*scale] as [number,number,number]);
    if(points.length<3)return null;
    return <Line key={section.key} points={points} color={SECTION_COLORS[section.key]||"#17694c"} lineWidth={2.5} />;
  })}</group>;
}

function Controls({ reset, angle, revision, targetY, radius }: { reset: number; angle:number; revision:number; targetY:number; radius:number }) {
  const controls = useRef<OrbitControlsType>(null);
  const camera = useThree(state => state.camera);
  const invalidate = useThree(state => state.invalidate);
  useEffect(() => {
    const orbit = controls.current;
    if (!orbit) return;
    const target = new THREE.Vector3(0, targetY, 0);
    const start = new THREE.Spherical().setFromVector3(camera.position.clone().sub(target));
    let delta = angle - start.theta;
    while (delta > Math.PI) delta -= Math.PI * 2;
    while (delta < -Math.PI) delta += Math.PI * 2;
    const duration = 320;
    const startedAt = performance.now();
    let frameId = 0;
    orbit.enabled = false;
    const step = (now: number) => {
      const t = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const theta = start.theta + delta * eased;
      camera.position.set(
        target.x + Math.sin(theta) * radius,
        target.y,
        target.z + Math.cos(theta) * radius,
      );
      orbit.target.copy(target);
      orbit.update();
      invalidate();
      if (t < 1) frameId = requestAnimationFrame(step);
      else orbit.enabled = true;
    };
    frameId = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frameId);
      orbit.enabled = true;
    };
  }, [reset, angle, revision, targetY, radius, camera, invalidate]);
  return (
    <OrbitControls
      ref={controls}
      target={[0, targetY, 0]}
      enablePan={false}
      enableZoom={false}
      minPolarAngle={Math.PI / 2}
      maxPolarAngle={Math.PI / 2}
      enableDamping
      dampingFactor={VIEWER_CONFIG.dampingFactor}
      rotateSpeed={VIEWER_CONFIG.rotateSpeed}
      minDistance={radius}
      maxDistance={radius}
      touches={{ ONE: THREE.TOUCH.ROTATE }}
    />
  );
}

function ClipController({ cutY, refreshKey }: { cutY:number; refreshKey:string }) {
  const gl = useThree(state => state.gl);
  const scene = useThree(state => state.scene);
  useEffect(() => {
    gl.localClippingEnabled = true;
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -cutY);
    const apply = () => {
      scene.traverse((object) => {
        const material = (object as THREE.Mesh).material as THREE.Material | THREE.Material[] | undefined;
        if (!material) return;
        const materials = Array.isArray(material) ? material : [material];
        for (const item of materials) {
          item.clippingPlanes = [plane];
          item.clipShadows = true;
          item.needsUpdate = true;
        }
      });
    };
    apply();
    const timers = [window.setTimeout(apply, 50), window.setTimeout(apply, 250)];
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      gl.localClippingEnabled = false;
    };
  }, [gl, scene, cutY, refreshKey]);
  return null;
}

export default function BodyViewer({
  url,
  wireframe,
  reset,
  targetHeightCm,
  showRings,
  sections,
  onSelectView,
  studio=false,
  technical=false, points=false, annotations, selectedMeasurement, fitBands, fitHeatmap,
}: {
  url?: string;
  wireframe: boolean;
  reset: number;
  autoRotate?: boolean;
  targetHeightCm?: number;
  showRings?: boolean;
  sections?: Section[];
  onSelectView?: () => void;
  studio?:boolean;
  technical?:boolean;points?:boolean;annotations?:MeasurementDetail[];selectedMeasurement?:string;
  fitBands?:FitBand[];
  fitHeatmap?:FitHeatmap;
}) {
  const [view,setView]=useState(0),[revision,setRevision]=useState(0);
  const [frame,setFrame]=useState<ViewerFrame>(()=>defaultFrame());
  const handleFrame=useCallback((next:ViewerFrame)=>setFrame((prev)=>(
    prev.targetY===next.targetY && prev.radius===next.radius && prev.cutY===next.cutY ? prev : next
  )),[]);
  useEffect(()=>{setView(0);},[reset]);
  return (
    <div className="body-viewer">
    <Canvas frameloop="demand" dpr={[1, 1.5]} camera={{ fov: VIEWER_CONFIG.fov }} gl={{ antialias: true, alpha: true, preserveDrawingBuffer:technical }} fallback={<p className="viewer-fallback">Trình duyệt chưa hỗ trợ WebGL. Hãy bật tăng tốc đồ họa hoặc mở bằng Chrome.</p>}>
      <hemisphereLight args={["#ffffff","#7c8e81",2.2]} />
      <directionalLight position={[-3, 4, 5]} intensity={2.2} />
      <directionalLight position={[3, 2, -3]} intensity={1.5} color="#f4f7f1" />
      <Suspense fallback={null}>
        {url ? <Result url={url} wireframe={wireframe} studio={studio} technical={technical} points={points} fitBands={fitBands} fitHeatmap={fitHeatmap} bodyHeightCm={targetHeightCm} onFrame={handleFrame}/> : <Sample wireframe={wireframe} studio={studio} technical={technical} points={points}/>}
      </Suspense>
      {url && showRings && !technical && sections && targetHeightCm && <MeasurementRings heightCm={targetHeightCm} sections={sections}/> }
      {technical&&showRings&&annotations&&annotations.filter(m=>m.points_m.length>1).map(m=><Line key={m.key} points={m.points_m.map(p=>p.map(v=>v*1.75/((targetHeightCm||175)/100)) as [number,number,number])} position={[0,.025,0]} color={m.color} lineWidth={selectedMeasurement===m.key?4.5:2} transparent opacity={!selectedMeasurement||selectedMeasurement===m.key?1:.35}/>) }
      {technical&&<gridHelper args={[6,30,"#c2cdbf","#d8e1d5"]} position={[0,-.001,0]}/>}
      {!points && <ContactShadows position={[0, 0.01, 0]} opacity={0.38} scale={2} blur={1.5} far={1} />}
      {!studio&&!technical&&<><mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}><ringGeometry args={[0.60, 0.605, 96]} /><meshBasicMaterial color="#bcc9bd" side={THREE.DoubleSide} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.61, 96]} /><meshBasicMaterial color="#ccd7cb" transparent opacity={0.45} /></mesh></>}
      <ClipController cutY={frame.cutY} refreshKey={`${showRings}-${selectedMeasurement||""}-${fitHeatmap?"h":"b"}-${points?"p":"s"}`}/>
      <Controls reset={reset} angle={VIEWS[view].angle} revision={revision} targetY={frame.targetY} radius={frame.radius} />
    </Canvas>
    {!technical&&url&&showRings&&sections&&<div className="body-legend" aria-label="Chu vi trên avatar"><span>Vòng đo trên avatar</span>{sections.map(s=><div key={s.key}><i style={{background:SECTION_COLORS[s.key]||"#17694c"}}/><span>{s.label}</span><strong>{s.model_cm} <small>cm</small></strong></div>)}</div>}
    <div className="body-view-presets" aria-label="Góc xem cơ thể">{VIEWS.map((v,i)=><button key={v.label} onClick={()=>{setView(i);setRevision(n=>n+1);onSelectView?.();}} aria-label={`Xem ${v.label.toLowerCase()}`} title={`Xem ${v.label.toLowerCase()}`}>{v.label}</button>)}</div>
    </div>
  );
}
