export default function SubjectDropdown({ subjects, value, onChange }) {
  return (
    <label className="control">
      <span>Subject</span>
      <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
        {subjects.length === 0 && <option value="">(none)</option>}
        {subjects.map((s) => (
          <option key={s.subject} value={s.subject}>
            {s.subject} · {s.n_channels} ch{s.has_recon ? ' · recon' : ''}
          </option>
        ))}
      </select>
    </label>
  );
}
