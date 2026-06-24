import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

const BASE_RADIUS = 1.6; // mm

// Default contacts stay faint so they read as quiet context; only highlighted
// states (selected / hovered / muscle) get a saturated, larger marker.
const COLOR = {
  muscle: '#ef4444',   // marked muscle -> red
  active: '#fde047',   // currently selected channel -> bright yellow
  hovered: '#22d3ee',  // hovered -> cyan
  normal: '#eaeff5',   // default -> very light, near-cortex tone
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
      // Highlighted states are larger; default contacts are smaller + faint.
      const scale = active ? 2.4 : hovered ? 1.9 : muscle ? 1.5 : 0.8;

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
      {/* No `vertexColors` here: the sphere geometry has no per-vertex colour
          attribute, so enabling it sends the per-instance setColorAt() colours
          down the USE_COLOR path and they render wrong. meshBasicMaterial +
          the automatic instanceColor shows each contact's exact colour. */}
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
}
