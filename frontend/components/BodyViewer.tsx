"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { Center, ContactShadows, Line, OrbitControls } from "@react-three/drei";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";
import type {MeasurementDetail} from "../lib/useBodyScan";
import type { FitBand } from "../lib/fitMap";
import type { OrbitControls as OrbitControlsType } from "three-stdlib";

export type Section = {key:string;label:string;target_cm:number;model_cm:number;fit_error_cm:number;points_m:[number,number,number][]};
const SECTION_COLORS: Record<string,string> = {chest_cm:"#194e3d",waist_cm:"#a0521e",hip_cm:"#285b7e",chest:"#194e3d",waist:"#a0521e",hip:"#285b7e"};
const VIEWS = [{label:"Trước",angle:0},{label:"Nghiêng",angle:Math.PI/2},{label:"Sau",angle:Math.PI},{label:"3/4",angle:Math.PI/4}];

function Surface({ object, wireframe, targetHeight, preserveOrigin = false, studio=false, technical=false, points=false, fitBands }: { object: THREE.Object3D; wireframe: boolean; targetHeight: number; preserveOrigin?: boolean; studio?:boolean;technical?:boolean;points?:boolean;fitBands?:FitBand[] }) {
  const model = useMemo(() => {
    const copy = object.clone(true);
    const bounds=new THREE.Box3().setFromObject(copy), height=bounds.max.y-bounds.min.y;
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
        if (fitBands?.length) {
          // Per-vertex fit colours: horizontal anatomical bands, one colour per
          // estimated verdict. Kept as geometry colours so the heat map survives
          // screenshots and wireframe/points modes.
          const position = geometry.getAttribute("position");
          const colors = new Float32Array(position.count * 3);
          const color = new THREE.Color();
          for (let i = 0; i < position.count; i++) {
            const normalizedY = (position.getY(i) - bounds.min.y) / Math.max(height, 1e-6);
            const band = fitBands.find((b) => normalizedY >= b.from && normalizedY < b.to);
            color.set(band?.color ?? "#c9d1c8");
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;
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
        const material = new THREE.MeshStandardMaterial({
          color: fitBands?.length ? "#ffffff" : technical?"#3d5c4e":studio?"#ffffff":"#4a6858",
          vertexColors: Boolean(fitBands?.length),
          roughness: 0.80,
          metalness: 0.04,
          wireframe,
          side: THREE.DoubleSide,
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
    const box = new THREE.Box3().setFromObject(copy);
    const sizeY = box.getSize(new THREE.Vector3()).y;
    if (sizeY > 0) {
      copy.scale.setScalar(targetHeight / sizeY);
    }
    if(points){
      const cloud=new THREE.Group();copy.updateMatrixWorld(true);
      copy.traverse(child=>{if(child instanceof THREE.Mesh){const geometry=child.geometry.clone();geometry.applyMatrix4(child.matrixWorld);cloud.add(new THREE.Points(geometry,new THREE.PointsMaterial({color:"#194e3d",size:.006,sizeAttenuation:true})));}});
      return cloud;
    }
    return copy;
  }, [object, targetHeight, preserveOrigin, studio,technical,points,fitBands]);

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

function Result({ url, wireframe,studio,technical,points,fitBands }: { url: string; wireframe: boolean;studio:boolean;technical:boolean;points:boolean;fitBands?:FitBand[] }) {
  const model = useLoader(GLTFLoader, url);
  return <Surface object={model.scene} wireframe={wireframe} targetHeight={1.75} preserveOrigin studio={studio} technical={technical} points={points} fitBands={fitBands}/>;
}

function MeasurementRings({ heightCm, sections }: { heightCm:number; sections:Section[] }) {
  const scale=1.75/(heightCm/100);
  return <group position={[0,.025,0]}>{sections.map(section=>{
    const points=section.points_m.map(p=>[p[0]*scale,p[1]*scale,p[2]*scale] as [number,number,number]);
    if(points.length<3)return null;
    return <Line key={section.key} points={points} color={SECTION_COLORS[section.key]||"#17694c"} lineWidth={2.5} />;
  })}</group>;
}

function Controls({ reset, autoRotate, angle, revision }: { reset: number; autoRotate: boolean; angle:number; revision:number }) {
  const controls = useRef<OrbitControlsType>(null);
  const camera = useThree(state => state.camera);
  useEffect(() => {
    camera.position.set(Math.sin(angle)*3.1, 0.95, Math.cos(angle)*3.1);
    if (controls.current) {
      controls.current.target.set(0, 0.88, 0);
      controls.current.update();
    }
  }, [reset, camera, angle, revision]);
  return <OrbitControls ref={controls} target={[0, 0.88, 0]} enablePan={false} minDistance={1.8} maxDistance={5} maxPolarAngle={Math.PI / 1.85} minPolarAngle={0.2} autoRotate={autoRotate} autoRotateSpeed={0.65} />;
}

export default function BodyViewer({
  url,
  wireframe,
  reset,
  autoRotate,
  targetHeightCm,
  showRings,
  sections,
  onSelectView,
  studio=false,
  technical=false, points=false, annotations, selectedMeasurement, fitBands,
}: {
  url?: string;
  wireframe: boolean;
  reset: number;
  autoRotate: boolean;
  targetHeightCm?: number;
  showRings?: boolean;
  sections?: Section[];
  onSelectView?: () => void;
  studio?:boolean;
  technical?:boolean;points?:boolean;annotations?:MeasurementDetail[];selectedMeasurement?:string;
  fitBands?:FitBand[];
}) {
  const [view,setView]=useState(0),[revision,setRevision]=useState(0);
  useEffect(()=>{setView(0);},[reset]);
  return (
    <div className="body-viewer">
    <Canvas frameloop={autoRotate?"always":"demand"} dpr={[1, 1.5]} camera={{ position: [0, 0.95, 3.1], fov: 42 }} gl={{ antialias: true, alpha: true, preserveDrawingBuffer:technical }} fallback={<p className="viewer-fallback">Trình duyệt chưa hỗ trợ WebGL. Hãy bật tăng tốc đồ họa hoặc mở bằng Chrome.</p>}>
      <hemisphereLight args={["#ffffff","#7c8e81",2.2]} />
      <directionalLight position={[-3, 4, 5]} intensity={2.2} />
      <directionalLight position={[3, 2, -3]} intensity={1.5} color="#f4f7f1" />
      <Suspense fallback={null}>
        {url ? <Result url={url} wireframe={wireframe} studio={studio} technical={technical} points={points} fitBands={fitBands}/> : <Sample wireframe={wireframe} studio={studio} technical={technical} points={points}/>}
      </Suspense>
      {url && showRings && !technical && sections && targetHeightCm && <MeasurementRings heightCm={targetHeightCm} sections={sections}/> }
      {technical&&showRings&&annotations&&annotations.filter(m=>m.points_m.length>1).map(m=><Line key={m.key} points={m.points_m.map(p=>p.map(v=>v*1.75/((targetHeightCm||175)/100)) as [number,number,number])} position={[0,.025,0]} color={m.color} lineWidth={selectedMeasurement===m.key?4.5:2} transparent opacity={!selectedMeasurement||selectedMeasurement===m.key?1:.35}/>) }
      {technical&&<gridHelper args={[6,30,"#c2cdbf","#d8e1d5"]} position={[0,-.001,0]}/>}
      {!points && <ContactShadows position={[0, 0.01, 0]} opacity={0.38} scale={2} blur={1.5} far={1} />}
      {!studio&&!technical&&<><mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}><ringGeometry args={[0.60, 0.605, 96]} /><meshBasicMaterial color="#bcc9bd" side={THREE.DoubleSide} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.61, 96]} /><meshBasicMaterial color="#ccd7cb" transparent opacity={0.45} /></mesh></>}
      <Controls reset={reset} autoRotate={autoRotate} angle={VIEWS[view].angle} revision={revision} />
    </Canvas>
    {!technical&&url&&showRings&&sections&&<div className="body-legend" aria-label="Chu vi trên avatar"><span>Vòng đo trên avatar</span>{sections.map(s=><div key={s.key}><i style={{background:SECTION_COLORS[s.key]||"#17694c"}}/><span>{s.label}</span><strong>{s.model_cm} <small>cm</small></strong></div>)}</div>}
    <div className="body-view-presets" aria-label="Góc xem cơ thể">{VIEWS.map((v,i)=><button key={v.label} onClick={()=>{setView(i);setRevision(n=>n+1);onSelectView?.();}} aria-label={`Xem ${v.label.toLowerCase()}`} title={`Xem ${v.label.toLowerCase()} · dừng tự xoay`}>{v.label}</button>)}</div>
    </div>
  );
}
