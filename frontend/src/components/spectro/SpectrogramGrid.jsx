import { api } from '../../api.js';

// Tiled thumbnails of every channel's spectrogram for the current tag.
// Click selects the channel (mirrors clicking the electrode on the brain).
export default function SpectrogramGrid({
  task,
  subject,
  tag,
  channels,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
}) {
  if (!task || !subject || !tag) return null;
  return (
    <div className="spectro-grid">
      {channels.map((ch) => {
        const cls = [
          'thumb',
          ch === selectedChannel ? 'selected' : '',
          ch === hoveredChannel ? 'hovered' : '',
          muscleSet.has(ch) ? 'muscle' : '',
        ].join(' ').trim();
        return (
          <button
            key={ch}
            className={cls}
            title={ch}
            onClick={() => onSelect(ch)}
            onMouseEnter={() => onHover(ch)}
            onMouseLeave={() => onHover(null)}
          >
            <img
              src={api.thumbUrl(task, subject, tag, ch)}
              alt={ch}
              loading="lazy"
              draggable={false}
            />
            <span className="thumb-label">{ch}</span>
          </button>
        );
      })}
    </div>
  );
}
