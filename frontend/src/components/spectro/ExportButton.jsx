import { useState } from 'react';
import { api } from '../../api.js';

// Writes the staged muscle set: contract-B CSV + channels.tsv writeback.
export default function ExportButton({ task, subject, muscleSet }) {
  const [status, setStatus] = useState(null); // {kind:'ok'|'err', text}
  const [busy, setBusy] = useState(false);
  const channels = [...muscleSet].sort();

  async function doExport() {
    if (!task || !subject) return;
    setBusy(true);
    setStatus(null);
    try {
      const res = await api.postMuscle(task, subject, channels);
      setStatus({
        kind: 'ok',
        text: `Saved ${res.channels.length} channel(s); updated ${res.runs_updated.length} run(s).`,
      });
    } catch (e) {
      setStatus({ kind: 'err', text: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="export-box">
      <button className="export-btn" disabled={!task || !subject || busy} onClick={doExport}>
        {busy ? 'Exporting…' : `Export ${channels.length} muscle channel(s)`}
      </button>
      {status && (
        <span className={`export-status ${status.kind}`}>{status.text}</span>
      )}
    </div>
  );
}
