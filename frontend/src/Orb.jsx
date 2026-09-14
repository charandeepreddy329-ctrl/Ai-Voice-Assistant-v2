import React, { Component, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
function Core({active,reduced}) {
  const ref=useRef();
  const points=useMemo(()=>{
    const data=new Float32Array(2400*3);
    for(let i=0;i<2400;i++) {const y=1-(i/2399)*2;const radius=Math.sqrt(1-y*y);const theta=Math.PI*(3-Math.sqrt(5))*i; data.set([Math.cos(theta)*radius*1.7,y*1.7,Math.sin(theta)*radius*1.7],i*3);}
    return data;
  },[]);
  useFrame(({clock})=>{if(ref.current&&!reduced){const t=clock.getElapsedTime();ref.current.rotation.y=t*.12;ref.current.rotation.z=Math.sin(t*.25)*.1;ref.current.scale.setScalar(1+Math.sin(t*(active?5:1.1))*(active?.055:.015));}});
  return <group ref={ref}><points><bufferGeometry><bufferAttribute attach="attributes-position" args={[points,3]}/></bufferGeometry><pointsMaterial color={active?'#d4fff3':'#76e6cc'} size={.025} transparent opacity={.8} blending={THREE.AdditiveBlending}/></points><mesh><sphereGeometry args={[1.48,48,48]}/><meshBasicMaterial color="#102d2c" transparent opacity={.24}/></mesh>{[0,1,2].map(i=><mesh key={i} rotation={[Math.PI/2+i*.42,.3+i*.6,0]}><torusGeometry args={[1.9+i*.12,.006,8,180]}/><meshBasicMaterial color="#a6ebda" transparent opacity={.25}/></mesh>)}</group>
}
class Boundary extends Component {state={failed:false}; static getDerivedStateFromError(){return {failed:true}} render(){return this.state.failed?<div className="fallback-orb"/>:this.props.children}}
export default function Orb({active}) {const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;return <Boundary><Canvas camera={{position:[0,0,5.6],fov:48}} dpr={[1,1.5]} frameloop={reduced?'demand':'always'} gl={{alpha:true,antialias:true}}><Core active={active} reduced={reduced}/></Canvas></Boundary>}
