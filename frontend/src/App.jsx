import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api.js';
import SubjectDropdown from './components/SubjectDropdown.jsx';
import BrainPanel from './components/brain/BrainPanel.jsx';
import SpectrogramPanel from './components/spectro/SpectrogramPanel.jsx';

export default function App() {
  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState('');
  const [manifest, setManifest] = useState(null);
  const [tag, setTag] = useState('');
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [hoveredChannel, setHoveredChannel] = useState(null);
  const [muscleSet, setMuscleSet] = useState(() => new Set());
  const [electrodes, setElectrodes] = useState(null);
  const [electrodesError, setElectrodesError] = useState(null);
  const [loadError, setLoadError] = useState(null);

  // --- bootstrap: subject list -------------------------------------------
  useEffect(() => {
    api
      .listSubjects()
      .then((list) => {
        setSubjects(list);
        if (list.length) setSubject((cur) => cur || list[0].subject);
      })
      .catch((e) => setLoadError(String(e.message || e)));
  }, []);

  // --- on subject change: manifest + muscle marks + electrodes ------------
  useEffect(() => {
    if (!subject) return;
    let alive = true;
    setManifest(null);
    setElectrodes(null);
    setElectrodesError(null);
    setSelectedChannel(null);
    setHoveredChannel(null);

    api
      .getManifest(subject)
      .then((m) => {
        if (!alive) return;
        setManifest(m);
        setTag((m.tags && m.tags[0]) || '');
      })
      .catch((e) => alive && setLoadError(String(e.message || e)));

    api
      .getMuscle(subject)
      .then((res) => alive && setMuscleSet(new Set(res.channels)))
      .catch(() => alive && setMuscleSet(new Set()));

    return () => {
      alive = false;
    };
  }, [subject]);

  // electrodes only when this subject has recon
  const hasRecon = !!manifest?.has_recon;
  useEffect(() => {
    if (!subject || !hasRecon) {
      setElectrodes(null);
      return;
    }
    let alive = true;
    api
      .getElectrodes(subject)
      .then((els) => alive && setElectrodes(els))
      .catch((e) => alive && setElectrodesError(String(e.message || e)));
    return () => {
      alive = false;
    };
  }, [subject, hasRecon]);

  const tags = manifest?.tags || [];
  const channels = manifest?.channels || [];

  const toggleMuscle = useCallback((channel, on) => {
    if (!channel) return;
    setMuscleSet((prev) => {
      const next = new Set(prev);
      if (on) next.add(channel);
      else next.delete(channel);
      return next;
    });
  }, []);

  const brainUrl = useMemo(
    () => (subject ? api.brainUrl(subject) : null),
    [subject],
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>Muscle Channel Marker</h1>
        <div className="topbar-controls">
          <SubjectDropdown subjects={subjects} value={subject} onChange={setSubject} />
          {manifest && (
            <span className="muted">
              {manifest.task} · {channels.length} channels
              {hasRecon ? ' · recon' : ' · no recon'}
            </span>
          )}
        </div>
      </header>

      {loadError && <div className="error-banner">Error: {loadError}</div>}

      <main className="layout">
        <BrainPanel
          subject={subject}
          hasRecon={hasRecon}
          brainUrl={brainUrl}
          electrodes={electrodes}
          electrodesError={electrodesError}
          selectedChannel={selectedChannel}
          muscleSet={muscleSet}
          hoveredChannel={hoveredChannel}
          onSelect={setSelectedChannel}
          onHover={setHoveredChannel}
        />
        <SpectrogramPanel
          subject={subject}
          tags={tags}
          tag={tag}
          onTag={setTag}
          channels={channels}
          selectedChannel={selectedChannel}
          muscleSet={muscleSet}
          hoveredChannel={hoveredChannel}
          onSelect={setSelectedChannel}
          onHover={setHoveredChannel}
          onToggleMuscle={toggleMuscle}
        />
      </main>
    </div>
  );
}
