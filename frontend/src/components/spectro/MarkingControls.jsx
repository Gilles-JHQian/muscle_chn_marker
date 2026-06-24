import { useState } from 'react';

// The 7 muscle-judgement criteria, transcribed from
// plan_muscle_gui/refs/readme.md Step 5.
const CRITERIA = [
  'Very high frequency (e.g. > 300 Hz) activations in the oral response phase.',
  'Located in anterior temporal (shank crossing the jaw).',
  'For temporal electrodes, strong motor activity but no auditory activity.',
  'At the beginning or end of a shank (maybe outside the cortex).',
  'Sudden and strong activity (real neural activity is usually persistent).',
  'Very large low-frequency activity that extends into the high-gamma band.',
  'Very similar activity across electrodes on a shank (spans ROIs / white matter '
    + '→ likely not brain).',
];

export default function MarkingControls({ channel, isMuscle, onToggle }) {
  const [showHelp, setShowHelp] = useState(false);
  return (
    <div className="marking-controls">
      <label className={`muscle-toggle${!channel ? ' disabled' : ''}`}>
        <input
          type="checkbox"
          disabled={!channel}
          checked={isMuscle}
          onChange={(e) => onToggle(channel, e.target.checked)}
        />
        <span>
          Mark <strong>{channel || '—'}</strong> as muscle
        </span>
      </label>
      <button className="help-btn" onClick={() => setShowHelp((v) => !v)}>
        {showHelp ? 'Hide' : 'Show'} criteria
      </button>
      {showHelp && (
        <div className="help-panel">
          <p className="help-intro">
            Consider a channel muscle if (combine features by the actual situation):
          </p>
          <ol>
            {CRITERIA.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
