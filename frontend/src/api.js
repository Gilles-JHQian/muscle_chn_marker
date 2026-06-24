// Thin fetch wrapper around the FastAPI backend. Same-origin in production
// (backend serves dist/); in dev Vite proxies /api -> :8001 (vite.config.js).
// All subject data is namespaced by task: /api/tasks/{task}/subjects/...

const BASE = '';

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`GET ${path} -> ${res.status} ${detail}`);
  }
  return res.json();
}

const sub = (task, s) => `/api/tasks/${task}/subjects/${s}`;

export const api = {
  listTasks: () => getJSON('/api/tasks'),
  listSubjects: (task) => getJSON(`/api/tasks/${task}/subjects`),
  getManifest: (task, s) => getJSON(`${sub(task, s)}/manifest`),
  getSpectra: (task, s, tag, ch) => getJSON(`${sub(task, s)}/spectra/${tag}/${ch}`),
  getElectrodes: (task, s) => getJSON(`${sub(task, s)}/electrodes.json`),
  getMuscle: (task, s) => getJSON(`${sub(task, s)}/muscle`),

  // URLs consumed directly by <img> / useGLTF, not fetched as JSON.
  thumbUrl: (task, s, tag, ch) => `${BASE}${sub(task, s)}/thumbs/${tag}/${ch}.png`,
  brainUrl: (task, s) => `${BASE}${sub(task, s)}/brain.glb`,

  async postMuscle(task, s, channels, writebackTsv = true) {
    const res = await fetch(`${BASE}${sub(task, s)}/muscle`, {
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
