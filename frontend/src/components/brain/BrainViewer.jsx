import { Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { TrackballControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import ElectrodeInstances from './ElectrodeInstances.jsx';

// Four fixed anatomical viewpoints (FreeSurfer RAS: +x=Right, +y=Anterior,
// +z=Superior). Camera looks at the cortex centre (origin after the group
// offset); `up` orients the view sensibly. `reset()` on each view's controls
// returns to exactly this framing.
const DIST = 320;
const VIEWS = [
  { key: 'L', label: 'Left', position: [-DIST, 0, 0], up: [0, 0, 1] },
  { key: 'R', label: 'Right', position: [DIST, 0, 0], up: [0, 0, 1] },
  { key: 'S', label: 'Top', position: [0, 0, DIST], up: [0, 1, 0] },
  { key: 'I', label: 'Bottom', position: [0, 0, -DIST], up: [0, 1, 0] },
];

// A directional light pinned to the camera so the cortex facing the viewer is
// always lit -- keeps gyri/sulci legible from every angle as you rotate.
function HeadLight({ intensity = 0.6 }) {
  const ref = useRef(null);
  const { camera } = useThree();
  useFrame(() => {
    if (ref.current) ref.current.position.copy(camera.position);
  });
  return <directionalLight ref={ref} intensity={intensity} />;
}

// Loads the pial GLB and renders cortex + electrodes in one group centred on the
// cortex bounding-box centre, so rotation pivots on the brain. Geometry is
// cloned per canvas (the four views are independent WebGL contexts) and smooth
// vertex normals are computed (the GLB ships positions only).
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
        obj.geometry = obj.geometry.clone();
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
    // opacity is applied live by the effect below, not by rebuilding here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene]);

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

// One of the four viewpoints: its own camera, trackball controls and reset.
function BrainView({ view, sceneProps }) {
  const controlsRef = useRef(null);
  return (
    <div className="brain-subview">
      <span className="subview-label">{view.label}</span>
      <button
        className="subview-reset"
        title={`Reset ${view.label} view`}
        onClick={() => controlsRef.current?.reset()}
      >
        ⟲
      </button>
      <Canvas
        camera={{ position: view.position, up: view.up, fov: 35, near: 1, far: 4000 }}
      >
        <ambientLight intensity={0.5} />
        <hemisphereLight args={['#ffffff', '#4b5563', 0.55]} />
        <HeadLight intensity={0.6} />
        <directionalLight position={[150, 200, 150]} intensity={0.2} />
        <Suspense fallback={null}>
          <Scene {...sceneProps} />
        </Suspense>
        {/* Screen-space trackball: free rotation with no fixed up-axis. Each
            view's controls are independent; reset() restores this view's
            default position/up/target captured at mount. */}
        <TrackballControls
          ref={controlsRef}
          makeDefault
          rotateSpeed={3.5}
          zoomSpeed={1.2}
          panSpeed={0.8}
          staticMoving
          minDistance={80}
          maxDistance={1200}
        />
      </Canvas>
    </div>
  );
}

export default function BrainViewer({
  brainUrl,
  electrodes,
  cortexOpacity = 0.2,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  const sceneProps = {
    brainUrl,
    electrodes,
    cortexOpacity,
    selectedChannel,
    muscleSet,
    hoveredChannel,
    onSelect,
    onHover,
  };
  return (
    <div className="brain-grid">
      {VIEWS.map((view) => (
        <BrainView key={view.key} view={view} sceneProps={sceneProps} />
      ))}
    </div>
  );
}
