import { Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { TrackballControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import ElectrodeInstances from './ElectrodeInstances.jsx';

// A directional light pinned to the camera so the cortex facing the viewer is
// always lit -- this is what keeps gyri/sulci legible from every angle (a fixed
// light leaves the back of the head in shadow as you rotate).
function HeadLight({ intensity = 0.6 }) {
  const ref = useRef(null);
  const { camera } = useThree();
  useFrame(() => {
    if (ref.current) ref.current.position.copy(camera.position);
  });
  return <directionalLight ref={ref} intensity={intensity} />;
}

// Loads the pial GLB and renders the cortex + electrodes in one group, centred
// on the cortex bounding-box centre so rotation pivots on the brain (not the
// off-centre electrode cluster). The GLB ships positions only, so we compute
// smooth vertex normals here -- without them the surface can't be shaded and
// appears to vanish at grazing angles.
function Scene({
  brainUrl,
  electrodes,
  cortexOpacity,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  const { scene } = useGLTF(brainUrl);

  const brain = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((obj) => {
      if (obj.isMesh) {
        obj.geometry.computeVertexNormals();
        obj.material = new THREE.MeshStandardMaterial({
          color: '#cbced3',
          roughness: 0.85,
          metalness: 0.0,
          transparent: true,
          opacity: cortexOpacity,
          depthWrite: true,
          side: THREE.DoubleSide,
        });
      }
    });
    return clone;
    // material is created once per loaded mesh; opacity is updated by the effect
    // below so dragging the slider doesn't rebuild geometry/normals.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene]);

  // Live opacity updates from the slider.
  useEffect(() => {
    brain.traverse((obj) => {
      if (obj.isMesh && obj.material) {
        obj.material.opacity = cortexOpacity;
        obj.material.transparent = cortexOpacity < 0.99;
        obj.material.depthWrite = cortexOpacity >= 0.99;
        obj.material.needsUpdate = true;
      }
    });
  }, [brain, cortexOpacity]);

  const center = useMemo(() => {
    const box = new THREE.Box3().setFromObject(brain);
    const c = new THREE.Vector3();
    box.getCenter(c);
    return c;
  }, [brain]);

  return (
    <group position={[-center.x, -center.y, -center.z]}>
      <primitive object={brain} />
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
  );
}

export default function BrainViewer({
  brainUrl,
  electrodes,
  cortexOpacity = 0.78,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  return (
    <Canvas
      camera={{ position: [-300, 0, 40], up: [0, 0, 1], fov: 35, near: 1, far: 4000 }}
    >
      <ambientLight intensity={0.5} />
      <hemisphereLight args={['#ffffff', '#4b5563', 0.55]} />
      <HeadLight intensity={0.6} />
      <directionalLight position={[150, 200, 150]} intensity={0.2} />
      <Suspense fallback={null}>
        <Scene
          brainUrl={brainUrl}
          electrodes={electrodes}
          cortexOpacity={cortexOpacity}
          selectedChannel={selectedChannel}
          muscleSet={muscleSet}
          hoveredChannel={hoveredChannel}
          onSelect={onSelect}
          onHover={onHover}
        />
      </Suspense>
      {/* Trackball (not orbit) controls: rotation is in screen space with no
          fixed up-vector, so horizontal drag always spins about the screen's
          vertical axis and vertical drag about the screen's horizontal axis,
          regardless of how the brain is currently oriented. Target defaults to
          (0,0,0) = the cortex centre after the group offset above. */}
      <TrackballControls
        makeDefault
        rotateSpeed={3.5}
        zoomSpeed={1.2}
        panSpeed={0.8}
        staticMoving
        minDistance={80}
        maxDistance={1200}
      />
    </Canvas>
  );
}
