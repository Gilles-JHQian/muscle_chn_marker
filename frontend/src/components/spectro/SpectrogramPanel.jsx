import TagSelector from '../TagSelector.jsx';
import SpectrogramGrid from './SpectrogramGrid.jsx';
import SpectrogramDetail from './SpectrogramDetail.jsx';
import MarkingControls from './MarkingControls.jsx';
import ExportButton from './ExportButton.jsx';

export default function SpectrogramPanel({
  task,
  subject,
  tags,
  tag,
  onTag,
  channels,
  selectedChannel,
  muscleSet,
  hoveredChannel,
  onSelect,
  onHover,
  onToggleMuscle,
}) {
  return (
    <section className="panel spectro-panel">
      <header className="panel-title">
        <span>Wavelet spectrograms</span>
        <TagSelector tags={tags} value={tag} onChange={onTag} />
      </header>

      <div className="spectro-grid-wrap">
        <SpectrogramGrid
          task={task}
          subject={subject}
          tag={tag}
          channels={channels}
          selectedChannel={selectedChannel}
          muscleSet={muscleSet}
          hoveredChannel={hoveredChannel}
          onSelect={onSelect}
          onHover={onHover}
        />
      </div>

      <div className="spectro-detail-wrap">
        <SpectrogramDetail task={task} subject={subject} tags={tags} channel={selectedChannel} />
      </div>

      <div className="spectro-actions">
        <MarkingControls
          channel={selectedChannel}
          isMuscle={selectedChannel ? muscleSet.has(selectedChannel) : false}
          onToggle={onToggleMuscle}
        />
        <ExportButton task={task} subject={subject} muscleSet={muscleSet} />
      </div>
    </section>
  );
}
