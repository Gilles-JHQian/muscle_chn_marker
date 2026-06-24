// Thin fetch wrapper around the FastAPI backend. Same-origin in production
// (backend serves dist/); in dev Vite proxies /api -> :8001 (vite.config.js).

const BASE = '';

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`GET ${path} -> ${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  listSubjects: () => getJSON('/api/subjects'),
  getManifest: (s) => getJSON(`/api/subjects/${s}/manifest`),
  getSpectra: (s, tag, ch) => getJSON(`/api/subjects/${s}/spectra/${tag}/${ch}`),
  getElectrodes: (s) => getJSON(`/api/subjects/${s}/electrodes.json`),
  getMuscle: (s) => getJSON(`/api/subjects/${s}/muscle`),

  // URLs consumed directly by <img> / useGLTF, not fetched as JSON.
  thumbUrl: (s, tag, ch) => `${BASE}/api/subjects/${s}/thumbs/${tag}/${ch}.png`,
  brainUrl: (s) => `${BASE}/api/subjects/${s}/brain.glb`,

  async postMuscle(s, channels, writebackTsv = true) {
    const res = await fetch(`${BASE}/api/subjects/${s}/muscle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channels, writeback_tsv: writebackTsv }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      throw new Error(`POST muscle -> ${res.status} ${detail}`);
    }
    return res.json();
  },
};
