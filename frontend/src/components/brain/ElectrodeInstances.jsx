import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

const BASE_RADIUS = 1.6; // mm

const COLOR = {
  muscle: '#ef4444',   // already-marked / staged muscle -> red
  active: '#facc15',   // currently selected channel -> yellow
  hovered: '#22d3ee',  // hovered -> cyan
  normal: '#cbd5e1',   // default -> light slate
};

// One InstancedMesh for all electrodes (fast for hundreds of contacts).
// selectedChannel highlight, muscleSet distinct colour, hover, two-way select.
export default function ElectrodeInstances({
  electrodes,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  const meshRef = useRef(null);
  const tmp = useMemo(() => new THREE.Object3D(), []);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh || !electrodes.length) return;
    const color = new THREE.Color();
    electrodes.forEach((e, i) => {
      const active = e.channel === selectedChannel;
      const hovered = e.channel === hoveredChannel;
      const muscle = muscleSet.has(e.channel);
      let key = 'normal';
      if (active) key = 'active';
      else if (hovered) key = 'hovered';
      else if (muscle) key = 'muscle';
      const scale = active ? 2.2 : hovered ? 1.8 : muscle ? 1.5 : 1.0;

      tmp.position.set(e.x, e.y, e.z);
      tmp.scale.setScalar(scale);
      tmp.updateMatrix();
      mesh.setMatrixAt(i, tmp.matrix);
      color.set(COLOR[key]);
      mesh.setColorAt(i, color);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [electrodes, selectedChannel, muscleSet, hoveredChannel, tmp]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, electrodes.length]}
      onPointerMove={(ev) => {
        ev.stopPropagation();
        onHover(electrodes[ev.instanceId]?.channel ?? null);
      }}
      onPointerOut={() => onHover(null)}
      onClick={(ev) => {
        ev.stopPropagation();
        const ch = electrodes[ev.instanceId]?.channel;
        if (ch) onSelect(ch);
      }}
    >
      <sphereGeometry args={[BASE_RADIUS, 16, 12]} />
      <meshStandardMaterial vertexColors roughness={0.5} metalness={0.0} />
    </instancedMesh>
  );
}
