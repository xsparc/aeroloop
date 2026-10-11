import {useEffect,useRef} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import type {Row} from './probe-contract.js';
const vec=(v:number[])=>new THREE.Vector3(v[0],v[2],-v[1]);
export default function ProbeScene({row,onFailure}:{row:Row;onFailure:()=>void}){
  const host=useRef<HTMLDivElement>(null),draw=useRef<(r:Row)=>void>(()=>{}),current=useRef(row);current.current=row;
  useEffect(()=>{const el=host.current!;let renderer:THREE.WebGLRenderer;try{renderer=new THREE.WebGLRenderer({antialias:true});}catch{onFailure();return;}
    renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor('#0b1724');el.append(renderer.domElement);
    const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(42,1,.001,100);camera.position.set(.8,.65,.9);
    const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,.07,0);controls.minDistance=.12;controls.maxDistance=4;controls.update();
    const grid=new THREE.GridHelper(2,20,0x457483,0x243847);scene.add(grid);
    const body=new THREE.Group(),collider=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(.4,.4,.1)),new THREE.LineBasicMaterial({color:0x68e2bc}));body.add(collider);
    const nose=new THREE.Mesh(new THREE.BoxGeometry(.1,.035,.035),new THREE.MeshBasicMaterial({color:0xfbbf24}));nose.position.x=.2;body.add(nose);scene.add(body);
    const points=new THREE.Group();scene.add(points);const convert=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.PI/2);
    const dispose=(root:THREE.Object3D)=>root.traverse(o=>{const mesh=o as THREE.Mesh;if(mesh.geometry)mesh.geometry.dispose();if(mesh.material){for(const m of Array.isArray(mesh.material)?mesh.material:[mesh.material])m.dispose();}});
    draw.current=(r:Row)=>{body.position.copy(vec(r.position));body.quaternion.copy(convert).multiply(new THREE.Quaternion(r.quaternion[1],r.quaternion[2],r.quaternion[3],r.quaternion[0]));for(const child of [...points.children]){dispose(child);points.remove(child);}
      for(const c of r.contacts){const color=c[0]<0?0xff7b9c:0x68e2bc,p=vec(c.slice(1,4));const marker=new THREE.Mesh(new THREE.SphereGeometry(.006,8,6),new THREE.MeshBasicMaterial({color}));marker.position.copy(p);points.add(marker);const direction=vec(c.slice(4,7)).multiplyScalar(Math.sign(c[0])||1);points.add(new THREE.ArrowHelper(direction,p,Math.min(.25,Math.abs(c[0])*10),color,.015,.01));}
      for(const c of r.anchors){const marker=new THREE.Mesh(new THREE.SphereGeometry(.004,8,6),new THREE.MeshBasicMaterial({color:0x70baff}));marker.position.copy(vec(c.slice(3,6)));points.add(marker);const direction=vec(c.slice(0,3)),size=direction.length();if(size>0)points.add(new THREE.ArrowHelper(direction.normalize(),marker.position,Math.min(.25,size*10),0x70baff,.015,.01));}
      renderer.render(scene,camera);};
    const render=()=>renderer.render(scene,camera),resize=new ResizeObserver(()=>{const w=el.clientWidth,h=el.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();render();});resize.observe(el);controls.addEventListener('change',render);draw.current(current.current);
    return()=>{resize.disconnect();controls.dispose();dispose(scene);renderer.dispose();renderer.domElement.remove();draw.current=()=>{};};
  },[onFailure]);useEffect(()=>draw.current(row),[row]);return <div className="probe-scene" ref={host} role="img" aria-label="Recorded collider, normal contacts and friction anchors in 3D"/>;
}
