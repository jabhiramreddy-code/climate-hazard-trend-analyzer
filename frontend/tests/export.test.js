import test from 'node:test';
import assert from 'node:assert/strict';
import { annualCsv, csvCell } from '../src/export.js';

test('CSV quotes commas, quotes and newlines and neutralizes formulas', () => {
  assert.equal(csvCell('a,"b"\nc'), '"a,""b""\nc"');
  assert.equal(csvCell(' =1+1'), "\"' =1+1\"");
  assert.equal(csvCell('@SUM(A1)'), "\"'@SUM(A1)\"");
  assert.equal(csvCell(null), '""');
});

test('annual export contains real values and methodology with CRLF rows', () => {
  const result = {
    annual: [{ year: 2021, events: 2, heatwave_days: 8, mean_duration: 4, mean_exceedance: 2.5, peak_temperature: 43, coverage: 1, eligible: true, rolling_events: null, rolling_duration: null, rolling_intensity: null }],
    location: { latitude: 28.6, longitude: 77.2 }, methodology: { threshold_c: 40.5, baseline: '1991–2020' }, source: { provider: 'Open-Meteo', model: 'ERA5' },
  };
  const csv = annualCsv(result);
  assert.ok(csv.includes('"2021","2","8","4","2.5","43","1","true"'));
  assert.ok(csv.includes('"40.5","1991–2020","Open-Meteo","ERA5"'));
  assert.equal(csv.split('\r\n').length, 3);
});

test('negative coordinates and temperatures remain numeric CSV values', () => {
  assert.equal(csvCell(-33.8688), '"-33.8688"');
  assert.equal(csvCell(-10), '"-10"');
});
