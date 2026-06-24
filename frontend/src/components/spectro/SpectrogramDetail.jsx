import { useEffect, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import { api } from '../../api.js';
import { PARULA } from '../../parula.js';

const Plot = createPlotlyComponent(Plotly);

const PLOT_CONFIG = {
  displayModeBar: true,
  displaylogo: false,
  scrollZoom: true,
  responsive: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toggleSpikelines'],
};

// One zoom/pan-able heatmap for a (tag, channel). Fetches its own slice.
function StageHeatmap({ subject, tag, channel, showColorbar }) {
  const [spec, setSpec] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    setSpec(null);
    setError(null);
    api
      .getSpectra(subject, tag, channel)
      .then((s) => alive && setSpec(s))
      .catch((e) => alive && setError(String(e.message || e)));
    return () => {
      alive = false;
    };
  }, [subject, tag, channel]);

  if (error) return <div className="stage stage-error">{tag}: {error}</div>;
  if (!spec) return <div className="stage stage-loading">{tag}…</div>;

  const [zmin, zmax] = spec.vlim;
  return (
    <div className="stage">
      <Plot
        data={[
          {
            type: 'heatmap',
            z: spec.data,
            x: spec.times,
            y: spec.freqs,
            zmin,
            zmax,
            colorscale: PARULA,
            zsmooth: 'best',
            showscale: showColorbar,
            colorbar: { title: 'dB', thickness: 8, len: 0.9 },
            hovertemplate: 't=%{x:.2f}s<br>f=%{y:.0f}Hz<br>%{z:.1f} dB<extra></extra>',
          },
        ]}
        layout={{
          title: { text: tag, font: { size: 13 } },
          margin: { l: 44, r: showColorbar ? 10 : 6, t: 26, b: 34 },
          xaxis: { title: 'Time (s)', zeroline: true, zerolinecolor: '#334155' },
          yaxis: { title: 'Freq (Hz)' },
          paper_bgcolor: '#ffffff',
          plot_bgcolor: '#ffffff',
          uirevision: `${subject}-${channel}-${tag}`,
          autosize: true,
        }}
        config={PLOT_CONFIG}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </div>
  );
}

export default function SpectrogramDetail({ subject, tags, channel }) {
  if (!channel) {
    return (
      <div className="detail-empty">
        Click a spectrogram thumbnail (or an electrode) to inspect its stages.
      </div>
    );
  }
  return (
    <div className="spectro-detail">
      {tags.map((tag, i) => (
        <StageHeatmap
          key={tag}
          subject={subject}
          tag={tag}
          channel={channel}
          showColorbar={i === tags.length - 1}
        />
      ))}
    </div>
  );
}
