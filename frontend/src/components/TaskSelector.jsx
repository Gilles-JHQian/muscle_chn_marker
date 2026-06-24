// Top-bar dropdown to switch between tasks. Only tasks that actually have data
// (n_subjects > 0) are selectable; configured-but-empty tasks are shown disabled
// so it's clear they exist but need data-prep first.
export default function TaskSelector({ tasks, value, onChange }) {
  return (
    <label className="control">
      <span>Task</span>
      <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
        {tasks.length === 0 && <option value="">(no data)</option>}
        {tasks.map((t) => (
          <option key={t.task} value={t.task} disabled={t.n_subjects === 0}>
            {t.label}
            {t.n_subjects === 0
              ? t.configured ? ' (no data)' : ' (not configured)'
              : ` (${t.n_subjects})`}
          </option>
        ))}
      </select>
    </label>
  );
}
