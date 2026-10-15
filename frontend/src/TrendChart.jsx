import { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';

const metrics = {
  events: { field: 'events', rolling: 'rolling_events', label: 'Heatwave events', unit: 'events', color: '#2259d1' },
  duration: { field: 'mean_duration', rolling: 'rolling_duration', label: 'Mean event duration', unit: 'days', color: '#167777' },
  intensity: { field: 'mean_exceedance', rolling: 'rolling_intensity', label: 'Mean exceedance above threshold', unit: '°C', color: '#b85a17' },
};

export default function TrendChart({ annual, metric }) {
  const canvas = useRef(null);
  const config = metrics[metric];
  useEffect(() => {
    const chart = new Chart(canvas.current, {
      type: 'line',
      data: {
        labels: annual.map(row => row.year),
        datasets: [
          { label: config.label, data: annual.map(row => row[config.field]), borderColor: config.color, backgroundColor: config.color,
            borderWidth: 2, pointRadius: annual.length > 35 ? 1 : 3, pointHoverRadius: 6, tension: 0,
            segment: { borderDash: context => !annual[context.p0DataIndex].eligible || !annual[context.p1DataIndex].eligible ? [3, 4] : undefined } },
          { label: '3-year rolling average', data: annual.map(row => row[config.rolling]), borderColor: '#64758a', borderWidth: 2,
            pointRadius: 0, borderDash: [6, 5], tension: 0, spanGaps: false },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { footer: items => {
            const row = annual[items[0]?.dataIndex];
            return row ? 'Valid observations: ' + Math.round(row.coverage * 100) + '%' + (row.eligible ? '' : ' (excluded from trends)') : '';
          } } },
        },
        scales: {
          x: { title: { display: true, text: 'Calendar year' }, grid: { display: false }, ticks: { maxTicksLimit: 12, color: '#64758a' } },
          y: { beginAtZero: true, title: { display: true, text: config.unit }, grid: { color: '#e4ecf4' }, ticks: { precision: metric === 'events' ? 0 : 1, color: '#64758a' } },
        },
      },
    });
    return () => chart.destroy();
  }, [annual, config, metric]);
  return <div className="chart-wrap"><canvas ref={canvas} role="img" aria-label={config.label + ' by year. Exact values are available in the annual data table below.'} /></div>;
}
