import React, { useState } from 'react';
import BrainViewer from './BrainViewer.jsx';

// Falls back to a friendly message if the GLB fails to load (no/partial recon).
class BrainErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) {
      this.setState({ failed: false });
    }
  }
  render() {
    if (this.state.failed) return this.props.fallback;
    return this.props.children;
  }
}

function Degraded({ message }) {
  return (
    <div className="brain-degraded">
      <h3>3D brain unavailable</h3>
      <p>{message}</p>
      <p className="muted">Spectrogram marking on the right still works fully.</p>
    </div>
  );
}

export default function BrainPanel({
  subject,
  hasRecon,
  brainUrl,
  electrodes,
  electrodesError,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  const [cortexOpacity, setCortexOpacity] = useState(0.15);
  let body;
  if (!subject) {
    body = <Degraded message="Select a subject to begin." />;
  } else if (!hasRecon) {
    body = <Degraded message={`No ECoG Recon for ${subject}.`} />;
  } else if (electrodesError) {
    body = <Degraded message={`Could not load electrodes: ${electrodesError}`} />;
  } else if (!electrodes) {
    body = <div className="panel-loading">Loading brain…</div>;
  } else {
    body = (
      <BrainErrorBoundary
        resetKey={subject}
        fallback={<Degraded message={`Could not load brain.glb for ${subject}.`} />}
      >
        <BrainViewer
          brainUrl={brainUrl}
          electrodes={electrodes}
          cortexOpacity={cortexOpacity}
          selectedChannel={selectedChannel}
          muscleSet={muscleSet}
          hoveredChannel={hoveredChannel}
          onSelect={onSelect}
          onHover={onHover}
        />
      </BrainErrorBoundary>
    );
  }

  return (
    <section className="panel brain-panel">
      <header className="panel-title">
        <span>Cortex &amp; electrodes</span>
        {selectedChannel && <span className="badge">{selectedChannel}</span>}
      </header>
      <div className="brain-canvas-wrap">{body}</div>
      {hasRecon && electrodes && (
        <footer className="brain-legend">
          <label className="opacity-slider" title="Cortex opacity">
            <span>Opacity</span>
            <input
              type="range"
              min="0.1"
              max="1"
              step="0.02"
              value={cortexOpacity}
              onChange={(e) => setCortexOpacity(parseFloat(e.target.value))}
            />
            <span className="opacity-val">{Math.round(cortexOpacity * 100)}%</span>
          </label>
          <span className="legend-sep" />
          <span><i className="dot dot-active" /> selected</span>
          <span><i className="dot dot-muscle" /> muscle</span>
          <span><i className="dot dot-normal" /> channel</span>
        </footer>
      )}
    </section>
  );
}
