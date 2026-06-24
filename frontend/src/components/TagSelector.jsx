// Event-tag tabs (Cue / Auditory / Go / Resp) that drive the spectrogram grid.
export default function TagSelector({ tags, value, onChange }) {
  return (
    <div className="tag-selector" role="tablist">
      {tags.map((tag) => (
        <button
          key={tag}
          role="tab"
          aria-selected={tag === value}
          className={`tag-btn${tag === value ? ' active' : ''}`}
          onClick={() => onChange(tag)}
        >
          {tag}
        </button>
      ))}
    </div>
  );
}
