export function csvCell(value) {
  let text = value == null ? '' : String(value);
  if (typeof value === 'string' && /^[\s]*[=+\-@]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

export function annualCsv(result) {
  const header = ['year', 'events', 'heatwave_days', 'mean_duration_days', 'mean_exceedance_c', 'peak_temperature_c', 'coverage', 'eligible_for_trend', 'rolling_events_3y', 'rolling_duration_3y', 'rolling_intensity_3y', 'latitude', 'longitude', 'threshold_c', 'baseline', 'source', 'model'];
  const rows = result.annual.map(row => [row.year, row.events, row.heatwave_days, row.mean_duration, row.mean_exceedance, row.peak_temperature, row.coverage, row.eligible, row.rolling_events, row.rolling_duration, row.rolling_intensity, result.location.latitude, result.location.longitude, result.methodology.threshold_c, result.methodology.baseline, result.source.provider, result.source.model]);
  return [header, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n';
}

export function downloadAnnualCsv(result) {
  const blob = new Blob(['\uFEFF', annualCsv(result)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'heatwaves-' + result.period.start_year + '-' + result.period.end_year + '.csv';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
