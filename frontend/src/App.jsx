import { useEffect, useRef, useState } from 'react';
import TrendChart from './TrendChart.jsx';
import { downloadAnnualCsv } from './export.js';

const cities = [
  { id: 'delhi', name: 'New Delhi, India', latitude: 28.6139, longitude: 77.2090 },
  { id: 'mumbai', name: 'Mumbai, India', latitude: 19.0760, longitude: 72.8777 },
  { id: 'bengaluru', name: 'Bengaluru, India', latitude: 12.9716, longitude: 77.5946 },
  { id: 'chennai', name: 'Chennai, India', latitude: 13.0827, longitude: 80.2707 },
  { id: 'ahmedabad', name: 'Ahmedabad, India', latitude: 23.0225, longitude: 72.5714 },
  { id: 'jaipur', name: 'Jaipur, India', latitude: 26.9124, longitude: 75.7873 },
  { id: 'kolkata', name: 'Kolkata, India', latitude: 22.5726, longitude: 88.3639 },
  { id: 'london', name: 'London, United Kingdom', latitude: 51.5074, longitude: -0.1278 },
  { id: 'sydney', name: 'Sydney, Australia', latitude: -33.8688, longitude: 151.2093 },
  { id: 'phoenix', name: 'Phoenix, United States', latitude: 33.4484, longitude: -112.0740 },
];
const metricLabels = { events: 'Frequency', duration: 'Duration', intensity: 'Intensity' };
const formatter = new Intl.NumberFormat('en', { maximumFractionDigits: 2 });
const number = value => value == null ? '—' : formatter.format(value);
const percent = value => number(value * 100) + '%';

function HeatMark({ large = false }) {
  return <svg className={large ? 'heat-mark large' : 'heat-mark'} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <circle cx="24" cy="24" r="9" stroke="currentColor" strokeWidth="2.5" />
    <path d="M24 4v6m0 28v6M4 24h6m28 0h6M10 10l4 4m20 20l4 4M10 38l4-4m20-20l4-4" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
  </svg>;
}

function TrendInsight({ result, metric }) {
  const trend = result.trends[metric];
  const units = { events: 'events', duration: 'days of mean duration', intensity: '°C of mean exceedance' };
  if (!trend) return <p className="insight">A regression needs at least five years with 90% or more valid daily observations. The selected interval has {result.summary.eligible_years} eligible years.</p>;
  const slope = trend.slope_per_decade;
  return <p className="insight">The fitted trend is <strong>{slope > 0 ? '+' : ''}{number(slope)} {units[metric]} per decade</strong>, using {trend.years_used} eligible years.
    {trend.r_squared == null ? ' R² is undefined because the annual values are constant.' : ' R² = ' + number(trend.r_squared) + '.'}
    {' This describes the selected record; it does not establish statistical significance or explain the cause.'}</p>;
}

export default function App() {
  const [region, setRegion] = useState('delhi');
  const [latitude, setLatitude] = useState('28.6139');
  const [longitude, setLongitude] = useState('77.2090');
  const [startYear, setStartYear] = useState('1990');
  const [endYear, setEndYear] = useState('2020');
  const [metric, setMetric] = useState('events');
  const [result, setResult] = useState(null);
  const [resultName, setResultName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showAllEvents, setShowAllEvents] = useState(false);
  const requestController = useRef(null);
  const latestYear = new Date().getUTCFullYear() - 1;
  useEffect(() => () => requestController.current?.abort(), []);

  function changeRegion(value) {
    setRegion(value);
    const city = cities.find(item => item.id === value);
    if (city) {
      setLatitude(String(city.latitude));
      setLongitude(String(city.longitude));
    }
  }

  async function submit(event) {
    event.preventDefault();
    const lat = Number(latitude), lon = Number(longitude), start = Number(startYear), end = Number(endYear);
    if (!latitude.trim() || !longitude.trim() || !Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      setError('Enter a latitude from −90 to 90 and a longitude from −180 to 180.');
      return;
    }
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1940 || end > latestYear || start > end) {
      setError('Choose ordered, complete calendar years from 1940 through ' + latestYear + '.');
      return;
    }
    const name = region === 'custom' ? number(lat) + '°, ' + number(lon) + '°' : cities.find(item => item.id === region).name;
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    const timer = setTimeout(() => controller.abort(), 100000);
    setLoading(true);
    setError('');
    setResult(null);
    setShowAllEvents(false);
    try {
      const response = await fetch('/api/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ latitude: lat, longitude: lon, start_year: start, end_year: end, hazard: 'heatwave' }),
      });
      const data = await response.json();
      if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : 'The server rejected these inputs. Check the location and year range.';
        throw new Error(detail);
      }
      setResult(data);
      setResultName(name);
    } catch (failure) {
      if (controller !== requestController.current) return;
      setError(failure.name === 'AbortError' ? 'This analysis timed out. Try again; a completed server result may already be cached.' : failure instanceof TypeError || failure instanceof SyntaxError ? 'The analysis service is unavailable. Check that the Python server is running, then try again.' : failure.message);
    } finally {
      clearTimeout(timer);
      if (controller === requestController.current) setLoading(false);
    }
  }

  const shownEvents = result ? (showAllEvents ? result.events : result.events.slice(0, 20)) : [];
  return <>
    <header className="site-header"><div className="header-inner"><a href="/" className="brand"><HeatMark /><span>Climate Hazard<br /><strong>Trend Analyzer</strong></span></a><span className="header-note">Historical data. Transparent methods.</span></div></header>
    <main className="page">
      <div className="page-heading"><div><h1>Heat in perspective.</h1><p>Explore how heatwaves have changed in a place you know.</p></div><span className="source-tag">ERA5 historical record</span></div>
      <div className="workspace">
        <aside className="controls"><h2>Set your analysis</h2><p className="muted">Choose a location and a period.</p>
          <form onSubmit={submit}>
            <fieldset disabled={loading}><legend className="sr-only">Analysis settings</legend>
              <label htmlFor="region">Location</label><select id="region" value={region} onChange={event => changeRegion(event.target.value)}>{cities.map(city => <option value={city.id} key={city.id}>{city.name}</option>)}<option value="custom">Custom coordinates</option></select>
              {region === 'custom' ? <div className="coordinate-fields"><div><label htmlFor="latitude">Latitude</label><input id="latitude" type="number" step="any" min="-90" max="90" value={latitude} required onChange={event => setLatitude(event.target.value)} /></div><div><label htmlFor="longitude">Longitude</label><input id="longitude" type="number" step="any" min="-180" max="180" value={longitude} required onChange={event => setLongitude(event.target.value)} /></div></div> : <p className="coordinates">{latitude}° latitude, {longitude}° longitude</p>}
              <label htmlFor="hazard">Hazard</label><select id="hazard" value="heatwave" disabled><option value="heatwave">Heatwave</option></select>
              <div className="year-fields"><div><label htmlFor="start-year">From year</label><input id="start-year" type="number" min="1940" max={latestYear} step="1" value={startYear} required onChange={event => setStartYear(event.target.value)} /></div><div><label htmlFor="end-year">To year</label><input id="end-year" type="number" min="1940" max={latestYear} step="1" value={endYear} required onChange={event => setEndYear(event.target.value)} /></div></div>
              <p className="field-help">Complete years from 1940 to {latestYear}.</p>
              <button className="primary-button" type="submit">{loading ? 'Analyzing…' : 'Analyze heatwaves'}</button>
            </fieldset>
          </form>
          <div className="definition-note"><HeatMark /><h3>What counts as a heatwave?</h3><p>Three or more consecutive days above the location’s 95th-percentile daily maximum temperature, using a fixed 1991–2020 baseline.</p></div>
        </aside>
        <section className="results" aria-label="Analysis results" aria-busy={loading}>
          {error && <div className="error-message" role="alert"><strong>Analysis unavailable</strong><p>{error}</p></div>}
          {loading && <div className="empty-state" role="status"><span className="spinner" aria-hidden="true" /><h2>Reading the historical record</h2><p>A first request downloads the selected years and reference baseline. This can take up to a minute; repeat requests use the stored results.</p></div>}
          {!loading && !result && <div className="empty-state"><HeatMark large /><h2>Start with a place and a period.</h2><p>Your analysis will show annual heatwave frequency, duration, intensity, and data coverage. Select your settings, then analyze the record.</p><div className="empty-method"><span>Fixed baseline</span><span>Consecutive-day detection</span><span>Coverage-aware trends</span></div></div>}
          {result && <>
            <div className="result-heading"><div><h2>{resultName}</h2><p>{result.period.start_year}–{result.period.end_year} <span className="dot">•</span> {result.annual.length} calendar years <span className="dot">•</span> {result.cache.analysis_hit ? 'Stored analysis' : 'Analysis complete'}</p></div><button className="secondary-button" onClick={() => downloadAnnualCsv(result)}>Export CSV</button></div>
            <div className="stats"><div><span>Heatwave events</span><strong>{number(result.summary.total_events)}</strong><small>Counted in their start year</small></div><div><span>Heatwave days</span><strong>{number(result.summary.heatwave_days)}</strong><small>Across the selected interval</small></div><div><span>Longest event</span><strong>{number(result.summary.longest_event)} <em>days</em></strong><small>Within this interval</small></div><div><span>95th-percentile threshold</span><strong>{number(result.methodology.threshold_c)} <em>°C</em></strong><small>Reference period 1991–2020</small></div></div>
            <div className="chart-panel"><div className="chart-heading"><h3>Heatwaves over time</h3><div className="metric-switch" role="group" aria-label="Chart metric">{Object.entries(metricLabels).map(([key, label]) => <button key={key} aria-pressed={metric === key} onClick={() => setMetric(key)}>{label}</button>)}</div></div>
              <div className={'chart-legend metric-' + metric}><span><i className="annual-key" />Annual {metricLabels[metric].toLowerCase()}</span><span><i className="rolling-key" />3-year rolling average</span></div>
              <TrendChart annual={result.annual} metric={metric} />
              <p className="chart-help">Hover for exact values. Dashed annual segments indicate a year with less than 90% coverage. {metric === 'duration' ? 'Duration is the mean of events starting that year; a year with no event has a value of zero.' : metric === 'intensity' ? 'Intensity is the mean temperature above the threshold on heatwave days; a year with no heatwave day has a value of zero.' : 'An event crossing New Year is counted once, in the year it starts.'}</p>
              <TrendInsight result={result} metric={metric} />
            </div>
            <div className="quality-note"><div><strong>Data coverage: {percent(result.quality.coverage)}</strong><p>{number(result.quality.valid_days)} valid days of {number(result.quality.expected_days)}. Baseline coverage: {percent(result.quality.baseline_coverage)}.</p></div><div><span>{number(result.quality.missing_days)} missing</span><span>{number(result.quality.invalid_days)} invalid</span><span>{number(result.quality.outlier_days)} outliers</span></div></div>
            {result.quality.low_coverage_years.length > 0 && <p className="warning" role="status">Excluded from trends because of low coverage: {result.quality.low_coverage_years.join(', ')}. Missing observations can hide or split events, so frequency can be biased in either direction.</p>}
            {result.summary.boundary_events > 0 && <p className="warning">{result.summary.boundary_events} event(s) touch the selected interval boundary. Their reported duration may be truncated.</p>}
            <details className="data-section"><summary>Annual data <span>{result.annual.length} rows</span></summary><div className="table-scroll" tabIndex="0" role="region" aria-label="Annual heatwave table"><table><caption className="sr-only">Annual heatwave statistics; missing observations can hide or split events.</caption><thead><tr><th scope="col">Year</th><th scope="col">Events</th><th scope="col">Heatwave days</th><th scope="col">Mean duration</th><th scope="col">Mean exceedance</th><th scope="col">Peak °C</th><th scope="col">Coverage</th></tr></thead><tbody>{result.annual.map(row => <tr key={row.year} className={row.eligible ? '' : 'low-coverage'}><th scope="row">{row.year}</th><td>{row.events}</td><td>{row.heatwave_days}</td><td>{number(row.mean_duration)} days</td><td>{number(row.mean_exceedance)} °C</td><td>{number(row.peak_temperature)}</td><td>{percent(row.coverage)}{!row.eligible && ' *'}</td></tr>)}</tbody></table></div></details>
            <details className="data-section"><summary>Detected events <span>{result.events.length} events</span></summary>{result.events.length === 0 ? <p className="section-copy">No qualifying heatwaves were observed in this interval under this definition.</p> : <><div className="table-scroll" tabIndex="0" role="region" aria-label="Detected heatwave events"><table><thead><tr><th scope="col">Start date</th><th scope="col">End date</th><th scope="col">Duration</th><th scope="col">Peak °C</th><th scope="col">Mean exceedance</th></tr></thead><tbody>{shownEvents.map(event => <tr key={event.start}><td>{event.start}</td><td>{event.end}</td><td>{event.duration} days{event.boundary_truncated && ' *'}</td><td>{number(event.peak_temperature)}</td><td>{number(event.mean_exceedance)} °C</td></tr>)}</tbody></table></div>{result.events.length > 20 && <button className="text-button" onClick={() => setShowAllEvents(value => !value)}>{showAllEvents ? 'Show first 20 events' : 'Show all ' + result.events.length + ' events'}</button>}</>}</details>
            <details className="data-section methodology"><summary>Methodology and limitations</summary><div className="section-copy"><p>The threshold is the pooled 95th percentile of daily maximum temperatures during 1991–2020. It is fixed for a location, calculated by linear rank interpolation, and compared using the unrounded value. This pooled threshold emphasizes the hottest season; it is not a seasonally varying threshold or an official local warning definition.</p><p>Missing observations and implausible temperatures outside −90 to 65 °C break an event. They are never interpolated. Heatwave days are allocated to their calendar year; event duration is allocated to the year the event begins. Trends use years with at least 90% coverage, three-year rolling windows, and ordinary least-squares regression.</p><p>ERA5 is gridded reanalysis rather than a local station measurement. The selected point represents a grid cell, not a city-wide or state-wide average. The analysis describes historical heat indicators and does not establish causal climate attribution or health risk.</p><p>Requested point: {result.location.latitude}°, {result.location.longitude}°. Provider grid point: {number(result.source.grid_latitude)}°, {number(result.source.grid_longitude)}°. Daily timezone: {result.source.timezone || 'not supplied'}. Computed: {new Date(result.cache.computed_at).toLocaleString()}.</p></div></details>
          </>}
        </section>
      </div>
      <footer className="footer"><span>Climate indicators are context, not a forecast.</span><span>Weather data by <a href="https://open-meteo.com/en/docs/historical-weather-api" target="_blank" rel="noreferrer">Open-Meteo</a>, ERA5 / <a href="https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5" target="_blank" rel="noreferrer">Copernicus C3S</a>. <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>.</span></footer>
    </main>
  </>;
}
