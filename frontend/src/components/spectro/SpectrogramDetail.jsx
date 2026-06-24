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
// The wavelet frequencies are geometrically spaced, so a log y-axis reproduces
// the thumbnail's equal-per-bin layout while still labelling true Hz.
function StageHeatmap({ task, subject, tag, channel }) {
  const [spec, setSpec] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    setSpec(null);
    setError(null);
    api
      .getSpectra(task, subject, tag, channel)
      .then((s) => alive && setSpec(s))
      .catch((e) => alive && setError(String(e.message || e)));
    return () => {
      alive = false;
    };
  }, [task, subject, tag, channel]);

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
            showscale: false,
            hovertemplate: 't=%{x:.2f}s<br>f=%{y:.0f}Hz<br>%{z:.1f} dB<extra></extra>',
          },
        ]}
        layout={{
          title: { text: tag, font: { size: 12 }, x: 0.5, xanchor: 'center', y: 0.97, yanchor: 'top' },
          margin: { l: 46, r: 6, t: 22, b: 30 },
          xaxis: {
            title: { text: 'Time (s)', standoff: 4 },
            zeroline: true,
            zerolinecolor: '#334155',
            automargin: true,
          },
          yaxis: {
            type: 'log',
            title: { text: 'Freq (Hz)', standoff: 2 },
            automargin: true,
          },
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

// A single shared colour bar to the right of all four heatmaps. They all use the
// same parula scale + vlim, so one static bar (CSS gradient) is clearer than a
// per-plot bar and avoids label overlap.
function ColorBar({ vlim }) {
  const stops = PARULA.map(([f, c]) => `${c} ${Math.round(f * 100)}%`).join(', ');
  const [lo, hi] = vlim;
  const mid = (lo + hi) / 2;
  return (
    <div className="spectro-colorbar">
      <span className="cb-title">dB</span>
      <div className="cb-body">
        <div className="cb-bar" style={{ background: `linear-gradient(to top, ${stops})` }} />
        <div className="cb-ticks">
          <span>{hi}</span>
          <span>{mid}</span>
          <span>{lo}</span>
        </div>
      </div>
    </div>
  );
}

const VLIM = [-2, 2]; // matches webui/preproc/config.WAVELET_VLIM and manifest vlim

export default function SpectrogramDetail({ task, subject, tags, channel }) {
  if (!channel) {
    return (
      <div className="detail-empty">
        Click a spectrogram thumbnail (or an electrode) to inspect its stages.
      </div>
    );
  }
  return (
    <div className="spectro-detail">
      <div className="spectro-stages">
        {tags.map((tag) => (
          <StageHeatmap key={tag} task={task} subject={subject} tag={tag} channel={channel} />
        ))}
      </div>
      <ColorBar vlim={VLIM} />
    </div>
  );
}
