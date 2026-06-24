"""Dependency-free binary glTF (.glb) writer.

Reused verbatim (logic) from
``brain_viewer/build_viewer_assets.py`` so the produced ``.glb`` loads with the
same three.js / ``@react-three/drei`` ``useGLTF`` path as the reference viewer.
Only ``struct``, ``json`` and ``numpy`` are needed -- no trimesh / pygltflib.

A single mesh with POSITION + indices is written; vertices are float32, indices
uint32, mode 4 (TRIANGLES).
"""

from __future__ import annotations

import json
import struct

import numpy as np


def _pad(data: bytes, fill: bytes = b"\x00") -> bytes:
    """Pad a byte string up to a 4-byte boundary (glTF chunk alignment)."""
    remainder = len(data) % 4
    if remainder == 0:
        return data
    return data + fill * (4 - remainder)


def merge_meshes(parts):
    """Concatenate several (vertices, faces) meshes into one, offsetting faces.

    ``parts`` is an iterable of ``(vertices Nx3, faces Mx3)`` arrays (e.g. lh + rh
    pial). Returns ``(vertices, faces)`` for the merged mesh.
    """
    verts, faces, offset = [], [], 0
    for v, f in parts:
        v = np.asarray(v, dtype=np.float32)
        f = np.asarray(f, dtype=np.int64) + offset
        verts.append(v)
        faces.append(f)
        offset += len(v)
    if not verts:
        raise ValueError("merge_meshes: no mesh parts supplied")
    return np.vstack(verts), np.vstack(faces)


def write_glb(path: str, vertices: np.ndarray, faces: np.ndarray) -> dict:
    """Write a minimal binary glTF (POSITION + indices, single mesh)."""
    vertices = np.ascontiguousarray(vertices, dtype=np.float32)
    indices = np.ascontiguousarray(np.asarray(faces).reshape(-1), dtype=np.uint32)

    v_bytes = vertices.tobytes()
    i_bytes = indices.tobytes()
    v_pad = _pad(v_bytes)
    bin_blob = v_pad + _pad(i_bytes)

    vmin = vertices.min(axis=0).tolist()
    vmax = vertices.max(axis=0).tolist()

    gltf = {
        "asset": {"version": "2.0", "generator": "muscle_chn_marker/webui.export.glb"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "brain"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
        "buffers": [{"byteLength": len(bin_blob)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(v_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(v_pad), "byteLength": len(i_bytes), "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": int(len(vertices)),
             "type": "VEC3", "min": vmin, "max": vmax},
            {"bufferView": 1, "componentType": 5125, "count": int(len(indices)),
             "type": "SCALAR"},
        ],
    }

    json_blob = _pad(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    total = 12 + 8 + len(json_blob) + 8 + len(bin_blob)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, total))          # header
        fh.write(struct.pack("<II", len(json_blob), 0x4E4F534A))     # JSON chunk
        fh.write(json_blob)
        fh.write(struct.pack("<II", len(bin_blob), 0x004E4942))      # BIN chunk
        fh.write(bin_blob)

    return {
        "n_vertices": int(len(vertices)),
        "n_faces": int(len(indices) // 3),
        "bounds": {"min": vmin, "max": vmax},
    }
