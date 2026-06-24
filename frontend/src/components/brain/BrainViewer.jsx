import { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import ElectrodeInstances from './ElectrodeInstances.jsx';

// Pial mesh loaded from the backend GLB (surfaceRAS frame; electrodes share it).
function BrainMesh({ url }) {
  const { scene } = useGLTF(url);
  const mesh = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((obj) => {
      if (obj.isMesh) {
        obj.material = new THREE.MeshStandardMaterial({
          color: '#d8d2cb',
          roughness: 0.95,
          metalness: 0.0,
          transparent: true,
          opacity: 0.45,
          side: THREE.DoubleSide,
        });
      }
    });
    return clone;
  }, [scene]);
  return <primitive object={mesh} />;
}

// Centre + frame the scene on the mesh/electrode centroid.
function sceneCenter(electrodes) {
  if (!electrodes.length) return [0, 0, 0];
  const n = electrodes.length;
  const sum = electrodes.reduce(
    (acc, e) => [acc[0] + e.x, acc[1] + e.y, acc[2] + e.z],
    [0, 0, 0],
  );
  return [sum[0] / n, sum[1] / n, sum[2] / n];
}

export default function BrainViewer({
  brainUrl,
  electrodes,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  const center = useMemo(() => sceneCenter(electrodes), [electrodes]);
  return (
    <Canvas camera={{ position: [0, 0, 320], fov: 35, near: 1, far: 4000 }}>
      <ambientLight intensity={0.85} />
      <directionalLight position={[200, 200, 300]} intensity={0.7} />
      <directionalLight position={[-200, -100, -200]} intensity={0.3} />
      <group position={[-center[0], -center[1], -center[2]]}>
        <Suspense fallback={null}>
          <BrainMesh url={brainUrl} />
        </Suspense>
        {electrodes.length > 0 && (
          <ElectrodeInstances
            electrodes={electrodes}
            selectedChannel={selectedChannel}
            muscleSet={muscleSet}
            hoveredChannel={hoveredChannel}
            onSelect={onSelect}
            onHover={onHover}
          />
        )}
      </group>
      <OrbitControls makeDefault enablePan target={[0, 0, 0]} />
    </Canvas>
  );
}
